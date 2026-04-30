#!/usr/bin/env python3
"""
Tournament Service
Picks top-rated strategies from strategy_library and demo-trades them on Oanda.

Flow:
  strategy_library (market=forex|multi, score >= MIN_SCORE)
    → skip strategies already filling an active slot
    → for each open slot: ask Groq if current H4 market matches entry conditions
    → if yes: fetch live Oanda M1 price → calculate entry/stop/TP
    → write to reviewed_signal_proposals (asset_type=forex)
    → auto_executor picks up and submits to trading engine → Hermes → Oanda

Slot rules:
  - MAX_CONCURRENT strategies at once (default 3)
  - Each active slot blocks its instrument from reuse
  - Strategies rotate by score: highest first, next after completion
  - Results tracked via reviewed_signal_proposals status history
"""

import os
import json
import uuid
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
    format="%(asctime)s [tournament] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "tournament_service.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("TournamentService")

SUPABASE_URL     = os.environ["SUPABASE_URL"]
SUPABASE_SVC_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GROQ_API_KEY     = os.environ["GROQ_API_KEY"]
OANDA_API_URL    = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com")
OANDA_API_KEY    = os.environ["OANDA_API_KEY"]
OANDA_ACCOUNT_ID = os.environ["OANDA_ACCOUNT_ID"]

POLL_SECS       = int(os.environ.get("TOURNAMENT_POLL_SECONDS", "300"))   # 5 min
MAX_CONCURRENT  = int(os.environ.get("TOURNAMENT_MAX_CONCURRENT", "3"))   # slots
MIN_SCORE       = float(os.environ.get("TOURNAMENT_MIN_SCORE", "40"))     # strategy_scores threshold
MIN_RR          = float(os.environ.get("TOURNAMENT_MIN_RR", "2.0"))       # reward:risk gate

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Forex pairs supported by Oanda demo
FOREX_PAIRS = {
    "EURUSD": "EUR_USD", "GBPUSD": "GBP_USD", "USDJPY": "USD_JPY",
    "AUDUSD": "AUD_USD", "USDCAD": "USD_CAD", "USDCHF": "USD_CHF",
    "NZDUSD": "NZD_USD", "EURJPY": "EUR_JPY", "GBPJPY": "GBP_JPY",
}

# Markets that are forex-compatible
FOREX_MARKETS = {"forex", "multi", "general", "fx"}

# Skip markets that can't be demo-traded on Oanda
SKIP_MARKETS = {"options", "equities", "stocks", "equity", "crypto", "futures"}

_svc_headers = {
    "apikey":        SUPABASE_SVC_KEY,
    "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
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


def _sb_post(table: str, row: dict) -> dict | None:
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_svc_headers, json=row, timeout=15,
    )
    if not r.ok:
        log.warning(f"POST {table} failed {r.status_code}: {r.text[:300]}")
        return None
    body = r.json()
    return body[0] if isinstance(body, list) else body

# ── Oanda helpers ─────────────────────────────────────────────────────────────

def _oanda_headers():
    return {"Authorization": f"Bearer {OANDA_API_KEY}"}


def get_open_instruments() -> set:
    """Return the set of Oanda instrument names (EUR_USD etc.) with open positions."""
    try:
        r = requests.get(
            f"{OANDA_API_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/openPositions",
            headers=_oanda_headers(), timeout=10,
        )
        if not r.ok:
            return set()
        return {p["instrument"] for p in r.json().get("positions", [])
                if int(p.get("long", {}).get("units", 0)) != 0
                or int(p.get("short", {}).get("units", 0)) != 0}
    except Exception as e:
        log.warning(f"Could not fetch open positions: {e}")
        return set()


def get_price_context() -> dict:
    """Fetch last 5 H4 candles for the 3 main pairs as market context for Groq."""
    context = {}
    for pair, instrument in [("EURUSD", "EUR_USD"), ("GBPUSD", "GBP_USD"), ("USDJPY", "USD_JPY")]:
        try:
            r = requests.get(
                f"{OANDA_API_URL}/v3/instruments/{instrument}/candles",
                headers=_oanda_headers(),
                params={"count": "5", "granularity": "H4", "price": "M"},
                timeout=10,
            )
            if not r.ok:
                continue
            candles = r.json().get("candles", [])
            context[pair] = [
                {
                    "time": c["time"][:16],
                    "open":  float(c["mid"]["o"]),
                    "high":  float(c["mid"]["h"]),
                    "low":   float(c["mid"]["l"]),
                    "close": float(c["mid"]["c"]),
                }
                for c in candles if c.get("complete", True)
            ]
        except Exception as e:
            log.warning(f"Price context fetch failed for {instrument}: {e}")
    return context


def get_live_price(oanda_symbol: str) -> tuple[float, float] | None:
    """Returns (bid, ask) from M1 close. Returns None on failure."""
    try:
        r = requests.get(
            f"{OANDA_API_URL}/v3/instruments/{oanda_symbol}/candles",
            headers=_oanda_headers(),
            params={"count": "1", "granularity": "M1", "price": "BA"},
            timeout=10,
        )
        if not r.ok:
            return None
        c = r.json()["candles"][0]
        return float(c["bid"]["c"]), float(c["ask"]["c"])
    except Exception as e:
        log.warning(f"Live price failed for {oanda_symbol}: {e}")
        return None

# ── Strategy selection ────────────────────────────────────────────────────────

def get_top_strategies(exclude_ids: set) -> list[dict]:
    """
    Return strategy_library rows joined with scores, filtered for forex
    compatibility and ordered by total_score descending.
    """
    rows = _sb_get("strategy_library", {
        "status": "neq.draft",
        "select": "id,strategy_name,strategy_id,setup_type,market,timeframes,entry_rules,exit_rules,risk_rules,indicators,summary,confidence",
        "limit":  "50",
    })
    if not rows:
        return []

    # Score lookup
    scores_raw = _sb_get("strategy_scores", {
        "select": "strategy_uuid,total_score,recommendation",
        "order":  "total_score.desc",
        "limit":  "100",
    })
    score_map = {s["strategy_uuid"]: s for s in scores_raw}

    results = []
    for row in rows:
        sid = row["id"]
        if sid in exclude_ids:
            continue
        market = (row.get("market") or "").lower()
        if any(m in market for m in SKIP_MARKETS):
            continue
        score_row = score_map.get(sid)
        total_score = float(score_row["total_score"]) if score_row else 0.0
        if total_score < MIN_SCORE:
            continue
        results.append({**row, "_score": total_score, "_recommendation": (score_row or {}).get("recommendation", "")})

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results


def get_active_strategy_ids() -> set:
    """
    Return strategy UUIDs that currently have a pending/proposed tournament slot.
    We identify these by the 'tournament:' prefix we put in strategy_id.
    """
    rows = _sb_get("reviewed_signal_proposals", {
        "asset_type": "eq.forex",
        "status":     "neq.executed",
        "select":     "strategy_id,status",
        "limit":      "50",
    })
    active = set()
    for r in rows:
        sid = r.get("strategy_id") or ""
        if sid.startswith("tournament:"):
            # extract UUID portion
            active.add(sid.split(":", 1)[1])
    return active


def get_active_proposal_instruments() -> set:
    """
    Return Oanda instrument names for proposals that are pending/in-flight.
    Prevents submitting a second trade on the same instrument.
    """
    rows = _sb_get("reviewed_signal_proposals", {
        "asset_type": "eq.forex",
        "status":     "neq.executed",
        "select":     "symbol,status",
        "limit":      "50",
    })
    instruments = set()
    for r in rows:
        sym = (r.get("symbol") or "").upper().replace("_", "")
        oanda = FOREX_PAIRS.get(sym)
        if oanda and (r.get("status") or "") not in ("blocked", "rejected"):
            instruments.add(oanda)
    return instruments

# ── Groq evaluation ───────────────────────────────────────────────────────────

EVALUATE_PROMPT = """\
You are a professional forex trading signal evaluator.

Given a trading strategy description and current H4 market data, decide whether
this strategy has an actionable trade entry signal right now.

Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{
  "has_entry": true | false,
  "symbol": "EURUSD" | "GBPUSD" | "USDJPY" | "AUDUSD" | "USDCAD" | "USDCHF" | "NZDUSD" | "EURJPY" | "GBPJPY" | null,
  "side": "BUY" | "SELL" | null,
  "timeframe": "H1" | "H4" | null,
  "risk_pct": 0.3,
  "reward_pct": 0.7,
  "reasoning": "one-sentence explanation"
}

Rules:
- has_entry = true ONLY when you can clearly identify a directional bias from the strategy rules AND current price action
- symbol: pick the single pair where the strategy's setup type is most visible in the H4 data
- side: BUY if bullish conditions match, SELL if bearish
- risk_pct: stop distance as % of price (0.2 to 0.8). Default 0.3
- reward_pct: target distance as % of price, must be >= 2 × risk_pct. Default 0.7
- Return has_entry: false if: strategy is not applicable to forex, conditions are unclear, or insufficient evidence
"""


def evaluate_strategy(strategy: dict, price_context: dict) -> dict | None:
    """
    Ask Groq to evaluate whether this strategy has a current entry signal.
    Returns a setup dict or None.
    """
    entry_rules = strategy.get("entry_rules") or {}
    conditions  = entry_rules.get("conditions", []) if isinstance(entry_rules, dict) else []
    exit_rules  = strategy.get("exit_rules") or {}
    exit_conds  = exit_rules.get("conditions", []) if isinstance(exit_rules, dict) else []

    # Build compact price summary
    price_lines = []
    for pair, candles in price_context.items():
        if candles:
            last = candles[-1]
            prev = candles[-2] if len(candles) > 1 else last
            trend = "↑" if last["close"] > prev["close"] else "↓"
            price_lines.append(
                f"{pair}: close={last['close']} high={last['high']} low={last['low']} trend={trend}"
            )

    user_content = f"""Strategy: {strategy.get('strategy_name', '?')}
Type: {strategy.get('setup_type', '?')} | Market: {strategy.get('market', '?')}
Timeframes: {strategy.get('timeframes', ['H1'])}
Indicators: {strategy.get('indicators', [])}

Entry conditions:
{chr(10).join(conditions[:6]) if conditions else strategy.get('summary','')[:300]}

Exit conditions:
{chr(10).join(exit_conds[:3]) if exit_conds else 'Standard TP/SL'}

Current H4 market (latest bar):
{chr(10).join(price_lines) if price_lines else 'No price data available'}

Does this strategy have a valid entry signal right now? Return JSON only."""

    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model":       "llama-3.1-8b-instant",
                "messages":    [
                    {"role": "system", "content": EVALUATE_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
                "temperature": 0.15,
                "max_tokens":  250,
            },
            timeout=20,
        )
        if not r.ok:
            log.warning(f"Groq evaluation failed {r.status_code}: {r.text[:200]}")
            return None
        text = r.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        log.warning(f"Groq evaluation error: {e}")
        return None

# ── Proposal builder ──────────────────────────────────────────────────────────

def build_proposal(strategy: dict, setup: dict, blocked_instruments: set) -> dict | None:
    """
    Build a reviewed_signal_proposals row from a strategy + Groq setup.
    """
    symbol = (setup.get("symbol") or "").upper().replace("_", "").replace("/", "")
    oanda_sym = FOREX_PAIRS.get(symbol)
    if not oanda_sym:
        log.info(f"  ↳ Symbol {symbol!r} not in approved pairs — skipping")
        return None
    if oanda_sym in blocked_instruments:
        log.info(f"  ↳ {oanda_sym} already has an open/pending position — skipping")
        return None

    side = (setup.get("side") or "").upper()
    if side not in ("BUY", "SELL"):
        return None

    prices = get_live_price(oanda_sym)
    if not prices:
        log.warning(f"  ↳ Could not fetch live price for {oanda_sym}")
        return None

    bid, ask = prices
    entry = ask if side == "BUY" else bid
    risk_pct   = max(float(setup.get("risk_pct")   or 0.3), 0.2) / 100
    reward_pct = max(float(setup.get("reward_pct") or 0.7), risk_pct * MIN_RR) / 100

    if side == "BUY":
        stop_loss   = round(entry * (1 - risk_pct),   5)
        take_profit = round(entry * (1 + reward_pct), 5)
    else:
        stop_loss   = round(entry * (1 + risk_pct),   5)
        take_profit = round(entry * (1 - reward_pct), 5)

    rr = reward_pct / risk_pct
    log.info(f"  ↳ {side} {symbol} entry={entry:.5f} stop={stop_loss:.5f} tp={take_profit:.5f} R:R={rr:.1f}")

    score    = strategy.get("_score", 50.0)
    conf     = min(max(round(score / 100, 3), 0.65), 0.95)  # floor at 0.65 so executor picks it up
    strat_id = f"tournament:{strategy['id']}"

    return {
        "symbol":      symbol,
        "side":        side,
        "timeframe":   (setup.get("timeframe") or (strategy.get("timeframes") or ["H1"])[0] or "H1"),
        "strategy_id": strat_id,
        "strategy_type": strategy.get("setup_type") or "general",
        "asset_type":  "forex",
        "entry_price": entry,
        "stop_loss":   stop_loss,
        "take_profit": take_profit,
        "ai_confidence": conf,
        "risk_notes":  setup.get("reasoning") or "",
        "status":      "proposed",
        "trace_id":    str(uuid.uuid4()),
    }

# ── Main poll loop ────────────────────────────────────────────────────────────

def run_once():
    log.info("Tournament: checking slots...")

    active_strategy_ids      = get_active_strategy_ids()
    active_proposal_instruments = get_active_proposal_instruments()
    open_oanda_instruments   = get_open_instruments()
    blocked_instruments      = active_proposal_instruments | open_oanda_instruments

    available_slots = MAX_CONCURRENT - len(active_strategy_ids)
    log.info(
        f"  Active strategies: {len(active_strategy_ids)}/{MAX_CONCURRENT} | "
        f"Blocked instruments: {blocked_instruments}"
    )
    if available_slots <= 0:
        log.info("  No open slots — waiting for trades to complete")
        return

    candidates = get_top_strategies(exclude_ids=active_strategy_ids)
    if not candidates:
        log.info("  No eligible strategies found (check MIN_SCORE or market filters)")
        return

    log.info(f"  {len(candidates)} eligible strategies, filling {available_slots} slot(s)")
    price_context = get_price_context()
    submitted = 0

    for strategy in candidates:
        if submitted >= available_slots:
            break

        name  = strategy.get("strategy_name", "?")
        score = strategy.get("_score", 0)
        log.info(f"Evaluating: {name!r} (score={score:.1f})")

        setup = evaluate_strategy(strategy, price_context)
        if not setup:
            log.info("  ↳ Groq evaluation failed")
            time.sleep(15)  # back off longer on rate limit errors
            continue

        if not setup.get("has_entry"):
            log.info(f"  ↳ No entry signal: {setup.get('reasoning','')}")
            time.sleep(10)
            continue

        proposal = build_proposal(strategy, setup, blocked_instruments)
        if not proposal:
            time.sleep(3)
            continue

        saved = _sb_post("reviewed_signal_proposals", proposal)
        if saved:
            log.info(
                f"  ✅ Proposal submitted: {proposal['side']} {proposal['symbol']} "
                f"conf={proposal['ai_confidence']} strategy={name!r}"
            )
            # Block this instrument for remaining iterations this cycle
            blocked_instruments.add(FOREX_PAIRS[proposal["symbol"]])
            submitted += 1
        else:
            log.warning(f"  ✗ Failed to save proposal for {name!r}")

        time.sleep(10)  # rate limit Groq (6K TPM on free tier)

    log.info(f"Tournament cycle complete — {submitted} new proposal(s) submitted")


def main():
    log.info(
        f"Tournament Service starting "
        f"(max_concurrent={MAX_CONCURRENT}, min_score={MIN_SCORE}, poll={POLL_SECS}s)"
    )
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Tournament run error: {e}", exc_info=True)
        log.info(f"Sleeping {POLL_SECS}s...")
        time.sleep(POLL_SECS)


if __name__ == "__main__":
    main()
