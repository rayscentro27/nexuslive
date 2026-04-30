"""
Signal Reviewer — calls Groq directly (stateless) for structured JSON signal review.

Uses Groq instead of routing through Hermes so that accumulated Hermes session
context doesn't inflate the request past Groq's 12K TPM free-tier limit.
Falls back to a local heuristic when Groq is unavailable.
"""

import os
import json
import logging
import requests

logger = logging.getLogger('SignalReviewer')

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL   = os.getenv('GROQ_SIGNAL_MODEL', 'llama-3.3-70b-versatile')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _supabase_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    r = requests.get(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    }, timeout=10)
    r.raise_for_status()
    return r.json()


def load_strategies(limit: int = 3) -> list[dict]:
    """Load recent research strategy titles for minimal prompt context."""
    try:
        rows = _supabase_get(
            f"research?select=title&order=created_at.desc&limit={limit}"
        )
        return [r.get('title', '') for r in rows]
    except Exception as e:
        logger.warning(f"Could not load strategies: {e}")
        return []


def review_signal(signal: dict) -> dict:
    """
    Send signal to Groq for AI review (stateless, no Hermes session overhead).

    Returns:
      {
        'action':          'approve' | 'reject' | 'hold',
        'confidence':      0.0-1.0,
        'strategy_match':  str or None,
        'reasoning':       str,
        'ai_available':    bool
      }
    """
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — using heuristic review")
        return _heuristic_review(signal)

    entry = signal.get('entry_price', 0) or 0
    sl    = signal.get('stop_loss', 0) or 0
    tp    = signal.get('take_profit', 0) or 0
    risk  = abs(entry - sl)
    rr    = f"1:{abs(tp - entry) / risk:.1f}" if risk else "n/a"

    strategies = load_strategies()
    strats_text = '; '.join(strategies) if strategies else 'none loaded'

    prompt = (
        f"Trading signal review. Reply ONLY with valid JSON, no markdown.\n"
        f"Symbol:{signal.get('symbol')} Side:{signal.get('side','').upper()} "
        f"TF:{signal.get('timeframe')}m Entry:{entry} SL:{sl} TP:{tp} "
        f"R:R:{rr} Confidence:{signal.get('confidence',0)}\n"
        f"Recent research: {strats_text}\n"
        f'JSON: {{"action":"approve|reject|hold","confidence":0.0-1.0,'
        f'"strategy_match":"name or null","reasoning":"one sentence"}}'
    )

    try:
        resp = requests.post(
            GROQ_API_URL,
            json={
                'model':       GROQ_MODEL,
                'messages':    [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens':  120,
            },
            headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        raw = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        match = __import__('re').search(r'\{[\s\S]*?\}', raw)
        if not match:
            raise ValueError(f"No JSON in Groq response: {raw[:80]!r}")

        result = json.loads(match.group())
        result['ai_available'] = True
        logger.info(
            f"Groq AI review: {result['action']} | "
            f"confidence={result.get('confidence')} | match={result.get('strategy_match')}"
        )
        return result

    except Exception as e:
        logger.warning(f"Groq review failed ({e}) — using heuristic")
        return _heuristic_review(signal)


def _heuristic_review(signal: dict) -> dict:
    """Fallback heuristic when Groq is unavailable.

    Confidence from TradingView webhooks is an integer 0-100; normalise to 0-1.
    Signals with no price data are held rather than rejected.
    """
    entry    = signal.get('entry_price', 0) or 0
    sl       = signal.get('stop_loss', 0) or 0
    tp       = signal.get('take_profit', 0) or 0
    conf_raw = signal.get('confidence', 0) or 0
    # Normalise: TradingView sends 0-100, internal signals may send 0-1
    conf = conf_raw / 100.0 if conf_raw > 1 else float(conf_raw)

    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    rr     = reward / risk if risk > 0 else 0

    # No price data — hold for next cycle
    if not entry or not sl or not tp:
        return {
            'action':         'hold',
            'confidence':     conf,
            'strategy_match': None,
            'reasoning':      "Heuristic: missing price data (entry/SL/TP). Holding for AI review.",
            'ai_available':   False,
        }

    # Hard reject only when confidence is zero AND R:R below 1:1
    if conf == 0 and rr < 1.0:
        return {
            'action':         'reject',
            'confidence':     conf,
            'strategy_match': None,
            'reasoning':      f"Heuristic: confidence {conf:.0%} and R:R {rr:.1f} both unacceptable.",
            'ai_available':   False,
        }

    return {
        'action':         'approve',
        'confidence':     conf,
        'strategy_match': signal.get('strategy_id'),
        'reasoning':      f"Heuristic: confidence {conf:.0%}, R:R {rr:.1f}.",
        'ai_available':   False,
    }
