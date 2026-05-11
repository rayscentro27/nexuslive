#!/usr/bin/env python3
"""
Strategy Ranker — scores extracted strategies via Hermes AI and stores results.

Reads strategy files from ./strategies/, scores each one 0-10,
saves to Supabase ranked_strategies table, and emits a system_event
for any strategy scoring >= HIGH_RANK_THRESHOLD.

Run: python3 strategy_ranker.py
     python3 strategy_ranker.py --threshold 6   (lower bar for paper testing)
     python3 strategy_ranker.py --dry-run        (score without writing to Supabase)
"""
import os, sys, json, re, argparse, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SUPABASE_URL   = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_KEY       = os.getenv("GROQ_API_KEY", "")
NVIDIA_KEY     = os.getenv("NVIDIA_API_KEY", "")
GEMINI_KEY_1   = os.getenv("GEMINI_API_KEY_1", "")
GEMINI_KEY_2   = os.getenv("GEMINI_API_KEY_2", "")

from api_health import is_available, mark_rate_limited, mark_ok
WORKER_NAME = "strategy_ranker"
STRATEGIES_DIR = Path(__file__).parent / "strategies"
HIGH_RANK_THRESHOLD = float(os.getenv("STRATEGY_RANK_THRESHOLD", "7.0"))
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
GROQ_MODEL = os.getenv("GROQ_STRATEGY_RANK_MODEL", os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))

RANK_SYSTEM_PROMPT = """\
You are a forex trading strategy analyst. Score the given strategy text from 0 to 10
based on its actionability for automated trading. Return JSON only — no prose.

Scoring criteria:
- Has specific entry conditions (indicator values, price levels, patterns): +2.5
- Has stop loss placement rules: +2.0
- Has take profit or exit rules: +2.0
- Specifies instrument(s) (EURUSD, GBPUSD, etc.): +1.0
- Specifies timeframe(s) (H1, H4, D1, etc.): +1.0
- Has backtested or verified results mentioned: +1.5

Deductions:
- Vague ("buy when market feels bullish"): -3
- No actionable signal whatsoever: score = 0-2
- Generic advice without rules: -2

Return exactly:
{
  "rank_score": 0.0-10.0,
  "has_entry": true or false,
  "has_stoploss": true or false,
  "has_tp": true or false,
  "instruments": ["EURUSD"],
  "timeframes": ["H1"],
  "reasons": ["entry: RSI below 30 on H1", "sl: below recent swing low"],
  "summary": "one sentence describing the strategy"
}"""


def _call_llm(strategy_text: str) -> dict | None:
    prompt = f"Score this trading strategy:\n\n{strategy_text[:3000]}"
    providers = []
    if OPENROUTER_KEY and is_available("openrouter"):
        providers.append({
            "url":      "https://openrouter.ai/api/v1/chat/completions",
            "key":      OPENROUTER_KEY,
            "model":    OPENROUTER_MODEL,
            "resource": "openrouter",
        })
    if GROQ_KEY and is_available("groq"):
        providers.append({
            "url":      "https://api.groq.com/openai/v1/chat/completions",
            "key":      GROQ_KEY,
            "model":    GROQ_MODEL,
            "resource": "groq",
        })
    if NVIDIA_KEY and is_available("nvidia"):
        providers.append({
            "url":      "https://integrate.api.nvidia.com/v1/chat/completions",
            "key":      NVIDIA_KEY,
            "model":    "meta/llama-3.3-70b-instruct",
            "resource": "nvidia",
        })
    for gkey, gres in [(GEMINI_KEY_1, "gemini1"), (GEMINI_KEY_2, "gemini2")]:
        if gkey and is_available(gres):
            providers.append({
                "url":      "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                "key":      gkey,
                "model":    "gemini-1.5-flash",
                "resource": gres,
            })

    for p in providers:
        try:
            body = json.dumps({
                "model": p["model"],
                "messages": [
                    {"role": "system", "content": RANK_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                "max_tokens": 400,
                "temperature": 0.1,
            }).encode()
            req = urllib.request.Request(
                p["url"], data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {p['key']}",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            mark_ok(WORKER_NAME, p["resource"])
            raw = data["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group())
        except urllib.error.HTTPError as e:
            code = e.code
            body_text = e.read().decode()[:200]
            if code in (429, 413):
                retry = 90 if code == 429 else 120
                print(f"  ⚠ {p['resource']} rate-limited (HTTP {code}) — backing off {retry}s")
                mark_rate_limited(WORKER_NAME, p["resource"], retry_seconds=retry, detail=body_text)
            else:
                print(f"  LLM error ({p['resource']} HTTP {code}): {body_text}")
            continue
        except Exception as e:
            print(f"  LLM error ({p['resource']}): {e}")
            continue
    return None


def _sb_post(table: str, row: dict) -> str | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        body = json.dumps(row).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{table}",
            data=body,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result[0].get("id") if result else None
    except Exception as e:
        print(f"  Supabase error: {e}")
        return None


def _emit_strategy_event(strategy_id: str, score: float, summary: str,
                          instruments: list, timeframes: list, strategy_text: str):
    """Emit a system_event so autonomy_worker routes this to the trading agent."""
    row = {
        "event_type": "high_ranked_strategy",
        "status":     "pending",
        "priority":   "high",
        "payload": {
            "strategy_id":    strategy_id,
            "rank_score":     score,
            "summary":        summary,
            "instruments":    instruments,
            "timeframes":     timeframes,
            "strategy_text":  strategy_text[:1000],
        },
        "source":     "strategy_ranker",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    event_id = _sb_post("system_events", row)
    if event_id:
        print(f"  ✅ system_event emitted → autonomy_worker (event_id={event_id})")
    return event_id


def already_ranked(filename: str) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        encoded = urllib.parse.quote(filename)
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/ranked_strategies?source_file=eq.{encoded}&select=id&limit=1",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return len(json.loads(r.read())) > 0
    except Exception:
        return False


def rank_strategy(filepath: Path, dry_run: bool = False, threshold: float = HIGH_RANK_THRESHOLD):
    filename = filepath.name
    # derive channel name from filename prefix "Channel Name - Video Title.summary"
    source_channel = filename.split(" - ")[0] if " - " in filename else "unknown"

    print(f"\n📊 Ranking: {filename[:70]}")

    if not dry_run and already_ranked(filename):
        print("  ↩ Already ranked — skipping")
        return None

    text = filepath.read_text(encoding="utf-8", errors="ignore")
    if len(text.strip()) < 100:
        print("  ⚠ Too short — skipping")
        return None

    result = _call_llm(text)
    if not result:
        print("  ❌ LLM unavailable — skipping")
        return None

    score = float(result.get("rank_score", 0))
    summary = result.get("summary", "")
    instruments = result.get("instruments", [])
    timeframes = result.get("timeframes", [])
    reasons = result.get("reasons", [])

    stars = "⭐" * round(score / 2)
    print(f"  Score: {score}/10 {stars}")
    print(f"  Summary: {summary}")
    print(f"  Instruments: {instruments}  Timeframes: {timeframes}")

    if dry_run:
        return result

    row = {
        "source_file":    filename,
        "source_channel": source_channel,
        "strategy_text":  text[:5000],
        "rank_score":     score,
        "rank_reasons":   {"reasons": reasons, "raw": result},
        "instruments":    instruments or None,
        "timeframes":     timeframes or None,
        "has_entry":      result.get("has_entry", False),
        "has_stoploss":   result.get("has_stoploss", False),
        "has_tp":         result.get("has_tp", False),
        "event_emitted":  False,
        "created_at":     datetime.now(timezone.utc).isoformat(),
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    }
    strategy_id = _sb_post("ranked_strategies", row)

    if strategy_id and score >= threshold:
        print(f"  🎯 High-rank strategy (≥{threshold}) — emitting system_event")
        _emit_strategy_event(strategy_id, score, summary, instruments, timeframes, text)

    return result


def main():
    parser = argparse.ArgumentParser(description="Rank trading strategies")
    parser.add_argument("--dry-run", action="store_true", help="Score without writing")
    parser.add_argument("--threshold", type=float, default=HIGH_RANK_THRESHOLD,
                        help="Min score to trigger paper trading event")
    parser.add_argument("--limit", type=int, default=50, help="Max files to process")
    args = parser.parse_args()

    if not STRATEGIES_DIR.exists():
        print(f"❌ Strategies directory not found: {STRATEGIES_DIR}")
        sys.exit(1)

    files = sorted(STRATEGIES_DIR.glob("*.summary"), key=lambda f: f.stat().st_mtime, reverse=True)
    files = files[:args.limit]

    print(f"🔍 Strategy Ranker — {len(files)} files to process (threshold={args.threshold})")
    if args.dry_run:
        print("⚠ DRY RUN — results will not be saved")

    ranked = 0
    high_rank = 0
    for f in files:
        result = rank_strategy(f, dry_run=args.dry_run, threshold=args.threshold)
        if result:
            ranked += 1
            if float(result.get("rank_score", 0)) >= args.threshold:
                high_rank += 1

    print(f"\n✅ Done — {ranked} ranked, {high_rank} high-rank events emitted")


if __name__ == "__main__":
    main()
