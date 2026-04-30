#!/usr/bin/env python3
"""
Research Signal Bridge
Converts research_artifacts (topic=trading) into tv_normalized_signals
so the autonomous trading lab can score and propose them.

Flow:
  research_artifacts (topic=trading)
    → Groq: extract trade setup (symbol, side, timeframe, strategy)
    → Oanda: fetch current price, calculate entry/stop/TP
    → tv_normalized_signals (status=enriched)
    → trading lab picks up and writes reviewed_signal_proposals
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
    format="%(asctime)s [bridge] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "research_signal_bridge.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("ResearchSignalBridge")

SUPABASE_URL        = os.environ["SUPABASE_URL"]
SUPABASE_SVC_KEY    = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GROQ_API_KEY        = os.environ["GROQ_API_KEY"]
OANDA_API_URL       = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com")
OANDA_API_KEY       = os.environ["OANDA_API_KEY"]

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
POLL_SECS  = int(os.environ.get("BRIDGE_POLL_SECONDS", "120"))
# Only these pairs are approved for Oanda demo
FOREX_PAIRS = {
    "EURUSD": "EUR_USD", "GBPUSD": "GBP_USD", "USDJPY": "USD_JPY",
    "AUDUSD": "AUD_USD", "USDCAD": "USD_CAD", "USDCHF": "USD_CHF",
    "NZDUSD": "NZD_USD", "EURJPY": "EUR_JPY", "GBPJPY": "GBP_JPY",
}

_svc_headers = {
    "apikey":        SUPABASE_SVC_KEY,
    "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}

# ── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_get(table: str, params: dict) -> list:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_svc_headers, params=params, timeout=15)
    if not r.ok:
        log.warning(f"GET {table} failed {r.status_code}: {r.text[:200]}")
        return []
    return r.json()


def _sb_post(table: str, row: dict) -> dict | None:
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=_svc_headers, json=row, timeout=15)
    if not r.ok:
        log.warning(f"POST {table} failed {r.status_code}: {r.text[:200]}")
        return None
    body = r.json()
    return body[0] if isinstance(body, list) else body


def _sb_patch(table: str, eq_field: str, eq_val: str, data: dict) -> bool:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_svc_headers, "Prefer": "return=minimal"},
        params={eq_field: f"eq.{eq_val}"},
        json=data, timeout=15,
    )
    return r.ok

# ── Oanda price fetch ─────────────────────────────────────────────────────────

def get_oanda_price(oanda_symbol: str) -> tuple[float, float] | None:
    """Returns (bid, ask) for the given Oanda instrument, or None on failure."""
    try:
        r = requests.get(
            f"{OANDA_API_URL}/v3/instruments/{oanda_symbol}/candles",
            headers={"Authorization": f"Bearer {OANDA_API_KEY}"},
            params={"count": "1", "granularity": "M1", "price": "BA"},
            timeout=10,
        )
        if not r.ok:
            return None
        c = r.json()["candles"][0]
        return float(c["bid"]["c"]), float(c["ask"]["c"])
    except Exception as e:
        log.warning(f"Oanda price fetch failed for {oanda_symbol}: {e}")
        return None

# ── Groq: extract trade setup from artifact ──────────────────────────────────

EXTRACT_PROMPT = """\
You are a professional forex/trading signal extractor.
Given research content about trading, identify if it describes a specific, actionable trade setup.

Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{
  "has_setup": true | false,
  "symbol": "EURUSD" | "GBPUSD" | "USDJPY" | "AUDUSD" | "USDCAD" | "USDCHF" | "NZDUSD" | "EURJPY" | "GBPJPY" | null,
  "side": "BUY" | "SELL" | null,
  "timeframe": "M15" | "H1" | "H4" | "D1" | null,
  "strategy_type": "trend_following" | "breakout" | "reversal" | "range" | "news_based" | null,
  "risk_pct": 0.5,
  "reward_pct": 1.5,
  "reasoning": "one-sentence summary of the setup"
}

Rules:
- has_setup must be true only if there is a clearly directional trade (BUY or SELL) on a specific forex pair
- symbol must be one of the listed forex pairs or null
- Use H1 as default timeframe if not specified
- risk_pct = expected stop distance as % of price (default 0.5%)
- reward_pct = expected target distance as % of price (default 1.0%, minimum 2x risk_pct)
- Return has_setup: false if the content is educational/conceptual with no specific trade direction
"""

def extract_setup_from_artifact(artifact: dict) -> dict | None:
    """Ask Groq to extract a trade setup from a research artifact. Returns setup dict or None."""
    content_parts = []
    if artifact.get("title"):
        content_parts.append(f"Title: {artifact['title']}")
    if artifact.get("summary"):
        content_parts.append(f"Summary: {artifact['summary']}")
    if artifact.get("key_points"):
        kp = artifact["key_points"]
        if isinstance(kp, list):
            content_parts.append("Key points:\n" + "\n".join(f"- {p}" for p in kp[:8]))
    if artifact.get("opportunity_notes"):
        on = artifact["opportunity_notes"]
        if isinstance(on, list):
            content_parts.append("Opportunities:\n" + "\n".join(f"- {n}" for n in on[:5]))

    if not content_parts:
        return None

    content = "\n\n".join(content_parts)[:3000]

    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": EXTRACT_PROMPT},
                    {"role": "user",   "content": content},
                ],
                "temperature": 0.1,
                "max_tokens": 300,
            },
            timeout=20,
        )
        if not r.ok:
            log.warning(f"Groq extraction failed {r.status_code}: {r.text[:200]}")
            return None

        text = r.json()["choices"][0]["message"]["content"].strip()
        # strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        log.warning(f"Groq extraction error: {e}")
        return None


def build_signal(artifact: dict, setup: dict) -> dict | None:
    """Build a tv_normalized_signals row from an artifact + Groq setup."""
    symbol = (setup.get("symbol") or "").upper().replace("_", "").replace("/", "")
    oanda_sym = FOREX_PAIRS.get(symbol)
    if not oanda_sym:
        log.info(f"  ↳ Symbol {symbol!r} not in approved pairs — skipping")
        return None

    prices = get_oanda_price(oanda_sym)
    if not prices:
        log.warning(f"  ↳ Could not fetch price for {oanda_sym}")
        return None

    bid, ask = prices
    side = (setup.get("side") or "").upper()
    if side not in ("BUY", "SELL"):
        return None

    entry = ask if side == "BUY" else bid
    risk_pct   = max(float(setup.get("risk_pct")   or 0.5), 0.3) / 100
    reward_pct = max(float(setup.get("reward_pct") or 1.0), risk_pct * 2) / 100

    if side == "BUY":
        stop_loss   = round(entry * (1 - risk_pct),   5)
        take_profit = round(entry * (1 + reward_pct), 5)
    else:
        stop_loss   = round(entry * (1 + risk_pct),   5)
        take_profit = round(entry * (1 - reward_pct), 5)

    rr = reward_pct / risk_pct
    log.info(f"  ↳ {side} {symbol} entry={entry} stop={stop_loss} tp={take_profit} R:R={rr:.1f}")

    return {
        "symbol":      symbol,
        "side":        side.lower(),
        "timeframe":   setup.get("timeframe") or "H1",
        "strategy_id": setup.get("strategy_type") or "research_derived",
        "entry_price": entry,
        "stop_loss":   stop_loss,
        "take_profit": take_profit,
        "confidence":  min(max(float(artifact.get("confidence") or 0.65), 0.0), 1.0),
        "session_label": "research",
        "source":      artifact.get("source") or artifact.get("channel_name") or "research",
        "status":      "enriched",
        "trace_id":    str(uuid.uuid4()),
        "meta": {
            "artifact_id":  artifact.get("id"),
            "artifact_title": artifact.get("title"),
            "reasoning":    setup.get("reasoning"),
            "bridged_at":   datetime.now(timezone.utc).isoformat(),
        },
    }

# ── Track already-bridged artifacts ──────────────────────────────────────────

def already_bridged_ids() -> set:
    """Return set of artifact IDs that have a real (non-skipped) signal written."""
    rows = _sb_get("tv_normalized_signals", {
        "source": "eq.research",
        "select": "meta,status",
        "limit":  "500",
    })
    ids = set()
    for row in rows:
        # Don't count skipped entries — allow retry with better model
        if (row.get("status") or "") == "skipped":
            continue
        meta = row.get("meta") or {}
        aid = meta.get("artifact_id")
        if aid:
            ids.add(str(aid))
    return ids

# ── Main poll loop ────────────────────────────────────────────────────────────

def run_once():
    log.info("Bridge: polling research_artifacts for trading setups...")
    bridged = already_bridged_ids()
    log.info(f"  Already bridged: {len(bridged)} artifacts")

    artifacts = _sb_get("research_artifacts", {
        "topic":   "eq.trading",
        "select":  "id,title,summary,key_points,opportunity_notes,confidence,source,channel_name,created_at",
        "order":   "created_at.desc",
        "limit":   "8",   # process 8 per cycle to stay within Groq TPM
    })

    new_signals = 0
    for art in artifacts:
        art_id = str(art.get("id", ""))
        if art_id in bridged:
            continue

        title = art.get("title") or "unknown"
        log.info(f"Processing artifact: {title!r} (id={art_id})")

        setup = extract_setup_from_artifact(art)
        if not setup:
            log.info("  ↳ Groq extraction failed — skipping")
            # mark as processed so we don't retry every poll
            _sb_post("tv_normalized_signals", {
                "symbol": "SKIP", "side": "skip", "status": "skipped",
                "source": "research", "meta": {"artifact_id": art_id, "skip_reason": "extraction_failed"},
                "trace_id": str(uuid.uuid4()),
            })
            continue

        if not setup.get("has_setup"):
            log.info(f"  ↳ No actionable setup found")
            _sb_post("tv_normalized_signals", {
                "symbol": "SKIP", "side": "skip", "status": "skipped",
                "source": "research", "meta": {"artifact_id": art_id, "skip_reason": "no_setup"},
                "trace_id": str(uuid.uuid4()),
            })
            continue

        signal = build_signal(art, setup)
        if not signal:
            continue

        saved = _sb_post("tv_normalized_signals", signal)
        if saved:
            log.info(f"  ✅ Signal written: id={saved.get('id')} {signal['side'].upper()} {signal['symbol']}")
            new_signals += 1
        else:
            log.warning(f"  ✗ Failed to write signal for {title!r}")

        time.sleep(6)  # rate limit: ~10 calls/min safely under 12K TPM

    log.info(f"Bridge run complete — {new_signals} new signal(s) written")
    return new_signals


def main():
    log.info("Research Signal Bridge starting...")
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Bridge run error: {e}", exc_info=True)
        log.info(f"Sleeping {POLL_SECS}s...")
        time.sleep(POLL_SECS)


if __name__ == "__main__":
    main()
