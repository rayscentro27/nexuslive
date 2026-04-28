#!/usr/bin/env python3
"""
Strategy Enhancer — AI researcher reviews ranked strategies and suggests improvements.

Reads mid-to-high ranked strategies (score >= 4.0) from Supabase that haven't
been enhanced yet, then asks an LLM to suggest concrete improvements:
  - Additional confirming indicators
  - Optimal trading session / time of day
  - Alternative or additional instruments (forex, crypto, stocks)
  - Refined entry trigger
  - Better SL/TP methodology

If the estimated enhanced score >= HIGH_RANK_THRESHOLD, re-emits a
high_ranked_strategy system_event with the improved strategy text.

Run: python3 strategy_enhancer.py
     python3 strategy_enhancer.py --min-score 5  (only enhance 5+)
     python3 strategy_enhancer.py --dry-run
"""
import os, sys, json, re, argparse, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from api_health import is_available, mark_rate_limited, mark_ok
WORKER_NAME = "strategy_enhancer"

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SUPABASE_URL        = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY        = os.getenv("SUPABASE_KEY", "")
OPENROUTER_KEY      = os.getenv("OPENROUTER_API_KEY", "")
GROQ_KEY            = os.getenv("GROQ_API_KEY", "")
NVIDIA_KEY          = os.getenv("NVIDIA_API_KEY", "")
COHERE_API_KEY      = os.getenv("COHERE_API_KEY", "")
GEMINI_KEY_1        = os.getenv("GEMINI_API_KEY_1", "")
GEMINI_KEY_2        = os.getenv("GEMINI_API_KEY_2", "")
HIGH_RANK_THRESHOLD = float(os.getenv("STRATEGY_RANK_THRESHOLD", "7.0"))

RERANK_QUERY = (
    "Actionable automated trading strategy with specific entry conditions, "
    "stop loss placement, take profit targets, defined instruments and timeframes"
)

ENHANCE_PROMPT = """\
You are an expert forex and multi-asset trading researcher.
A strategy has been submitted for enhancement. Your job is to make it more precise,
robust, and actionable without changing its core logic.

Provide specific, concrete suggestions only — no generic advice. Return JSON only.

Return exactly:
{
  "additional_indicators": [
    {"name": "RSI(14)", "rule": "must be below 30 for buy, above 70 for sell", "why": "confirms oversold/overbought"}
  ],
  "optimal_sessions": ["London open (08:00-10:00 GMT)", "New York open (13:00-15:00 GMT)"],
  "additional_instruments": [
    {"symbol": "GBPUSD", "type": "forex", "why": "correlates with original setup"},
    {"symbol": "BTCUSD", "type": "crypto", "why": "momentum strategy also applies in trending crypto"},
    {"symbol": "SPY", "type": "stock", "why": "broad market context for risk-on/off"}
  ],
  "entry_refinement": "Wait for a candlestick close above the 20 EMA with RSI crossing 50 upward",
  "sl_tp_improvement": "Use ATR(14) x 1.5 for SL, ATR(14) x 3.0 for TP instead of fixed pips",
  "enhanced_strategy_text": "Full rewritten strategy incorporating all improvements",
  "estimated_enhanced_score": 8.5,
  "summary_of_changes": "Added RSI confirmation, restricted to London/NY session overlap, extended to GBPUSD and crypto"
}"""


def _cohere_rerank(candidates: list[dict], limit: int) -> list[dict]:
    """
    Rerank strategy candidates by actionability using Cohere Rerank v3.
    Returns up to `limit` rows sorted by relevance score descending.
    Falls back to original score ordering if Cohere is unavailable.
    """
    if not COHERE_API_KEY or not is_available("cohere") or not candidates:
        return candidates[:limit]

    texts = [c.get("strategy_text", "")[:1000] for c in candidates]
    try:
        body = json.dumps({
            "model":            "rerank-v3.5",
            "query":            RERANK_QUERY,
            "documents":        [{"text": t} for t in texts],
            "top_n":            limit,
            "return_documents": False,
        }).encode()
        req = urllib.request.Request(
            "https://api.cohere.com/v2/rerank",
            data=body,
            headers={
                "Authorization": f"Bearer {COHERE_API_KEY}",
                "Content-Type":  "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())

        mark_ok(WORKER_NAME, "cohere")
        reranked = sorted(result["results"], key=lambda x: x["relevance_score"], reverse=True)
        ordered = [candidates[item["index"]] for item in reranked]
        scores  = [round(item["relevance_score"], 3) for item in reranked]
        print(f"  🎯 Cohere reranked {len(candidates)} → top {len(ordered)} "
              f"(scores: {scores[:5]})")
        return ordered

    except urllib.error.HTTPError as e:
        code = e.code
        if code in (429, 413):
            mark_rate_limited(WORKER_NAME, "cohere", retry_seconds=60,
                              detail=e.read().decode()[:200])
            print(f"  ⚠ Cohere rate-limited (HTTP {code}) — falling back to score order")
        else:
            print(f"  Cohere error HTTP {code} — falling back to score order")
        return candidates[:limit]
    except Exception as e:
        print(f"  Cohere rerank failed ({e}) — falling back to score order")
        return candidates[:limit]


def _call_llm(strategy_text: str, original_score: float, rank_reasons: dict) -> dict | None:
    reasons_str = json.dumps(rank_reasons.get("reasons", []))[:500]
    prompt = (
        f"Original score: {original_score}/10\n"
        f"Scoring notes: {reasons_str}\n\n"
        f"Original strategy:\n{strategy_text[:2500]}\n\n"
        f"Enhance this strategy."
    )
    providers = []
    if OPENROUTER_KEY and is_available("openrouter"):
        providers.append({
            "url":      "https://openrouter.ai/api/v1/chat/completions",
            "key":      OPENROUTER_KEY,
            "model":    "meta-llama/llama-3.3-70b-instruct",
            "resource": "openrouter",
        })
    if GROQ_KEY and is_available("groq"):
        providers.append({
            "url":      "https://api.groq.com/openai/v1/chat/completions",
            "key":      GROQ_KEY,
            "model":    "llama-3.3-70b-versatile",
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
                    {"role": "system", "content": ENHANCE_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                "max_tokens": 900,
                "temperature": 0.3,
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


def _sb_get(path: str) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  Supabase GET error: {e}")
        return []


def _sb_patch(path: str, body: dict) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        data = json.dumps(body).encode()
        req  = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}",
            data=data,
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "return=minimal",
            },
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        print(f"  Supabase PATCH error: {e}")
        return False


def _sb_post(table: str, row: dict) -> str | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        body = json.dumps(row).encode()
        req  = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{table}",
            data=body,
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "return=representation",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result[0].get("id") if result else None
    except Exception as e:
        print(f"  Supabase POST error: {e}")
        return None


def _emit_enhanced_event(strategy_id: str, enhanced_score: float, summary: str,
                          enhanced_text: str, instruments: list, timeframes: list):
    row = {
        "event_type": "high_ranked_strategy",
        "status":     "pending",
        "priority":   "high",
        "payload": {
            "strategy_id":    strategy_id,
            "rank_score":     enhanced_score,
            "summary":        summary,
            "instruments":    instruments,
            "timeframes":     timeframes,
            "strategy_text":  enhanced_text[:1000],
            "source":         "strategy_enhancer",
        },
        "source":     "strategy_enhancer",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    event_id = _sb_post("system_events", row)
    if event_id:
        print(f"  ✅ Enhanced system_event emitted (event_id={event_id})")
    return event_id


def enhance_strategy(row: dict, dry_run: bool = False, threshold: float = HIGH_RANK_THRESHOLD):
    strategy_id   = row["id"]
    source_file   = row.get("source_file", "unknown")
    original_score = float(row.get("rank_score", 0))
    strategy_text  = row.get("strategy_text", "")
    rank_reasons   = row.get("rank_reasons") or {}
    instruments    = row.get("instruments") or []
    timeframes     = row.get("timeframes")  or []

    print(f"\n🔬 Enhancing: {source_file[:65]} (score={original_score})")

    enhancement = _call_llm(strategy_text, original_score, rank_reasons)
    if not enhancement:
        print("  ❌ LLM unavailable — skipping")
        return None

    enhanced_score = float(enhancement.get("estimated_enhanced_score", original_score))
    summary        = enhancement.get("summary_of_changes", "")
    enhanced_text  = enhancement.get("enhanced_strategy_text", strategy_text)

    # Merge in any additional instruments the LLM found
    extra_instruments = [
        i["symbol"] for i in enhancement.get("additional_instruments", [])
        if isinstance(i, dict) and i.get("symbol")
    ]
    all_instruments = list(dict.fromkeys(instruments + extra_instruments))

    print(f"  Enhanced score: {enhanced_score}/10  (was {original_score})")
    print(f"  Changes: {summary[:120]}")
    print(f"  Instruments now: {all_instruments}")
    if enhancement.get("optimal_sessions"):
        print(f"  Sessions: {enhancement['optimal_sessions']}")

    if dry_run:
        return enhancement

    now = datetime.now(timezone.utc).isoformat()
    _sb_patch(
        f"ranked_strategies?id=eq.{strategy_id}",
        {
            "enhancement":    enhancement,
            "enhanced_score": enhanced_score,
            "enhanced_at":    now,
            "updated_at":     now,
        },
    )

    if enhanced_score >= threshold:
        print(f"  🎯 Enhanced score >= {threshold} — emitting system_event for paper testing")
        _emit_enhanced_event(
            strategy_id, enhanced_score, summary,
            enhanced_text, all_instruments, timeframes,
        )

    return enhancement


def main():
    parser = argparse.ArgumentParser(description="Enhance ranked trading strategies")
    parser.add_argument("--dry-run",   action="store_true", help="Enhance without writing")
    parser.add_argument("--min-score", type=float, default=4.0, help="Min rank_score to enhance")
    parser.add_argument("--limit",     type=int,   default=20,  help="Max strategies to process")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    # Fetch more candidates than needed so Cohere can rerank by actionability
    fetch_limit = max(args.limit * 3, 50)
    rows = _sb_get(
        f"ranked_strategies"
        f"?rank_score=gte.{args.min_score}"
        f"&enhanced_at=is.null"
        f"&order=rank_score.desc"
        f"&limit={fetch_limit}"
        f"&select=id,source_file,rank_score,strategy_text,rank_reasons,instruments,timeframes"
    )

    print(f"🔬 Strategy Enhancer — {len(rows)} candidates fetched (min_score={args.min_score})")
    rows = _cohere_rerank(rows, limit=args.limit)
    print(f"  Processing top {len(rows)} after rerank")
    if args.dry_run:
        print("⚠ DRY RUN — results will not be saved")

    enhanced = 0
    re_emitted = 0
    for row in rows:
        result = enhance_strategy(row, dry_run=args.dry_run, threshold=HIGH_RANK_THRESHOLD)
        if result:
            enhanced += 1
            if float(result.get("estimated_enhanced_score", 0)) >= HIGH_RANK_THRESHOLD:
                re_emitted += 1

    print(f"\n✅ Done — {enhanced} enhanced, {re_emitted} re-emitted for paper testing")


if __name__ == "__main__":
    main()
