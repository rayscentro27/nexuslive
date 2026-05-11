#!/usr/bin/env python3
"""
Auto Executor
Polls reviewed_signal_proposals for AI-approved forex signals and
forwards them to the trading engine for Oanda demo execution.

Flow:
  reviewed_signal_proposals (ai_confidence >= 0.65, status != blocked/executed)
    → validate R:R >= 2.0, symbol approved
    → POST http://localhost:5000/webhook/tradingview
    → PATCH reviewed_signal_proposals.status = 'executed'

Safety:
  - Oanda demo account only (NEXUS_DRY_RUN=false, OANDA_API_URL=fxpractice)
  - Only approved forex pairs
  - Trading engine does its own risk gate (R:R, position limits, daily loss)
  - Max AUTO_EXECUTE_PER_RUN signals per poll cycle
"""

import os
import time
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [executor] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "auto_executor.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("AutoExecutor")

SUPABASE_URL     = os.environ["SUPABASE_URL"]
SUPABASE_SVC_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
ENGINE_URL       = os.environ.get("TRADING_ENGINE_URL", "http://127.0.0.1:5000")

POLL_SECS            = int(os.environ.get("EXECUTOR_POLL_SECONDS", "60"))
MIN_CONFIDENCE       = float(os.environ.get("EXECUTOR_MIN_CONFIDENCE", "0.65"))
MIN_RR               = float(os.environ.get("EXECUTOR_MIN_RR", "2.0"))
MAX_PER_RUN          = int(os.environ.get("AUTO_EXECUTE_PER_RUN", "2"))

APPROVED_SYMBOLS = {
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD",
    "USD_CAD", "USD_CHF", "NZD_USD", "EUR_JPY", "GBP_JPY",
    # plain format (no underscore) also accepted
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
    "USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY",
}

_svc_headers = {
    "apikey":        SUPABASE_SVC_KEY,
    "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
    "Content-Type":  "application/json",
}

# ── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_get(table: str, params: dict) -> list:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_svc_headers, params=params, timeout=15,
    )
    if not r.ok:
        log.warning(f"GET {table} failed {r.status_code}: {r.text[:200]}")
        return []
    return r.json()


def _sb_patch(table: str, eq_field: str, eq_val: str, data: dict) -> bool:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_svc_headers, "Prefer": "return=minimal"},
        params={eq_field: f"eq.{eq_val}"},
        json=data, timeout=15,
    )
    if not r.ok:
        log.warning(f"PATCH {table} failed {r.status_code}: {r.text[:200]}")
    return r.ok

# ── Proposal validation ───────────────────────────────────────────────────────

def validate_proposal(p: dict) -> tuple[bool, str]:
    """Return (ok, reason)."""
    symbol = (p.get("symbol") or "").upper().replace("/", "").replace("_", "")
    if symbol + "_" not in {s.replace("_", "") + "_" for s in APPROVED_SYMBOLS} and \
       symbol not in APPROVED_SYMBOLS and (symbol[:3] + "_" + symbol[3:]) not in APPROVED_SYMBOLS:
        return False, f"symbol {symbol!r} not in approved list"

    side = (p.get("side") or "").upper()
    if side not in ("BUY", "SELL"):
        return False, f"invalid side {side!r}"

    entry = p.get("entry_price")
    stop  = p.get("stop_loss")
    tp    = p.get("take_profit")
    if not all([entry, stop, tp]):
        return False, "missing entry/stop/tp"

    try:
        risk   = abs(float(entry) - float(stop))
        reward = abs(float(tp) - float(entry))
        if risk <= 0:
            return False, "zero risk"
        rr = reward / risk
        if rr < MIN_RR:
            return False, f"R:R {rr:.2f} < {MIN_RR}"
    except (TypeError, ValueError) as e:
        return False, f"price parse error: {e}"

    conf = float(p.get("ai_confidence") or 0)
    if conf < MIN_CONFIDENCE:
        return False, f"confidence {conf:.2f} < {MIN_CONFIDENCE}"

    return True, "ok"

# ── Execute one proposal ──────────────────────────────────────────────────────

def execute_proposal(p: dict) -> bool:
    """POST signal to trading engine and mark proposal as executed."""
    proposal_id = p.get("id")
    symbol      = (p.get("symbol") or "").upper().replace("/", "")
    side        = (p.get("side") or "").upper()

    payload = {
        "symbol":     symbol,
        "action":     side,
        "entry":      float(p["entry_price"]),
        "stop":       float(p["stop_loss"]),
        "target":     float(p["take_profit"]),
        "timeframe":  p.get("timeframe") or "H1",
        "strategy":   p.get("strategy_id") or "auto_research",
        "confidence": int((float(p.get("ai_confidence") or 0.7)) * 100),
        "_source":    "auto_executor",
        "_proposal_id": str(proposal_id),
    }

    log.info(f"Executing: {side} {symbol}  entry={payload['entry']}  stop={payload['stop']}  tp={payload['target']}")

    try:
        r = requests.post(
            f"{ENGINE_URL}/webhook/tradingview",
            json=payload, timeout=10,
        )
        if r.ok:
            log.info(f"  ✅ Engine accepted — {r.json().get('status')}")
        else:
            log.warning(f"  ✗ Engine rejected {r.status_code}: {r.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        log.error(f"  ✗ Engine unreachable: {e}")
        return False

    # Mark proposal as executed regardless of engine decision
    # (engine may reject on risk; that's intentional — we don't retry)
    _sb_patch("reviewed_signal_proposals", "id", str(proposal_id), {
        "status":     "executed",
        "risk_notes": (p.get("risk_notes") or "") + f" [auto_executed {datetime.now(timezone.utc).isoformat()[:19]}]",
    })
    return True

# ── Main poll loop ────────────────────────────────────────────────────────────

def run_once():
    # Check engine is alive
    try:
        r = requests.get(f"{ENGINE_URL}/health", timeout=5)
        if not r.ok:
            log.warning("Trading engine health check failed — skipping this cycle")
            return
    except requests.exceptions.RequestException:
        log.warning("Trading engine unreachable — skipping this cycle")
        return

    proposals = _sb_get("reviewed_signal_proposals", {
        "asset_type": "eq.forex",
        "status":     "neq.executed",
        "select":     "id,symbol,side,timeframe,strategy_id,entry_price,stop_loss,take_profit,ai_confidence,status,risk_notes",
        "order":      "ai_confidence.desc",
        "limit":      "20",
    })

    # Also exclude 'blocked' via client-side filter since Supabase doesn't support multi-neq easily
    candidates = [
        p for p in proposals
        if (p.get("status") or "pending") not in ("executed", "blocked", "rejected")
    ]

    if not candidates:
        log.info("No proposals ready for execution")
        return

    log.info(f"{len(candidates)} proposal(s) available — evaluating...")

    executed = 0
    for p in candidates:
        if executed >= MAX_PER_RUN:
            log.info(f"Reached MAX_PER_RUN={MAX_PER_RUN} — stopping this cycle")
            break

        ok, reason = validate_proposal(p)
        if not ok:
            log.info(f"  Skip {p.get('symbol')} {p.get('side')}: {reason}")
            continue

        if execute_proposal(p):
            executed += 1
        time.sleep(2)   # brief gap between orders

    log.info(f"Executor cycle complete — {executed} order(s) submitted")


def main():
    log.info(f"Auto Executor starting  (min_confidence={MIN_CONFIDENCE}, min_rr={MIN_RR}, max_per_run={MAX_PER_RUN})")
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Executor run error: {e}", exc_info=True)
        log.info(f"Sleeping {POLL_SECS}s...")
        time.sleep(POLL_SECS)


if __name__ == "__main__":
    main()
