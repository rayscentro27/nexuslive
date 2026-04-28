"""
Signal Reviewer — sends a tv_normalized_signals row to Hermes for AI review.
Returns a structured review: confidence, action, strategy_match, reasoning.
"""

import os
import json
import urllib.request
import urllib.error
import logging

logger = logging.getLogger('SignalReviewer')

HERMES_GATEWAY_URL   = os.getenv('HERMES_GATEWAY_URL', 'http://localhost:8642')
HERMES_TOKEN = os.getenv('HERMES_GATEWAY_TOKEN', '')
HERMES_MODEL = os.getenv('HERMES_MODEL', 'hermes')
SUPABASE_URL   = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY   = os.getenv('SUPABASE_KEY', '')


def _supabase_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def load_strategies(limit: int = 20) -> list[dict]:
    """Load research strategies from Supabase for context."""
    try:
        rows = _supabase_get(
            f"research?select=title,content&order=created_at.desc&limit={limit}"
        )
        return [{'title': r.get('title', ''), 'summary': (r.get('content') or '')[:300]} for r in rows]
    except Exception as e:
        logger.warning(f"Could not load strategies: {e}")
        return []


def review_signal(signal: dict) -> dict:
    """
    Send signal to Hermes for AI review.

    Returns:
      {
        'action':          'approve' | 'reject' | 'hold',
        'confidence':      0.0-1.0,
        'strategy_match':  str or None,
        'reasoning':       str,
        'ai_available':    bool
      }
    """
    if not HERMES_TOKEN:
        logger.warning("HERMES_GATEWAY_TOKEN not set — using heuristic review")
        return _heuristic_review(signal)

    strategies = load_strategies()
    strategies_text = '\n'.join(
        f"- {s['title']}: {s['summary']}" for s in strategies
    ) or "No strategies loaded."

    prompt = f"""You are a trading signal analyst. Review this signal and decide whether to approve, reject, or hold it.

Signal:
- Symbol: {signal.get('symbol')}
- Side: {signal.get('side', '').upper()}
- Timeframe: {signal.get('timeframe')}m
- Entry: {signal.get('entry_price')}
- Stop Loss: {signal.get('stop_loss')}
- Take Profit: {signal.get('take_profit')}
- Session: {signal.get('session_label', 'unknown')}
- Source Confidence: {signal.get('confidence', 0)}

Known Research Strategies:
{strategies_text}

Respond with a JSON object ONLY:
{{
  "action": "approve" | "reject" | "hold",
  "confidence": <float 0.0-1.0>,
  "strategy_match": "<strategy name if matched, else null>",
  "reasoning": "<1-2 sentence explanation>"
}}

Rules for rejection: unclear setup, SL too tight, TP unrealistic, no strategy match with low source confidence.
Return ONLY the JSON. No explanation, no markdown."""

    try:
        body = json.dumps({
            'model':       HERMES_MODEL,
            'messages':    [{'role': 'user', 'content': prompt}],
            'temperature': 0.1
        }).encode()

        req = urllib.request.Request(
            f"{HERMES_GATEWAY_URL}/v1/chat/completions",
            data=body,
            headers={
                'Content-Type':  'application/json',
                'Authorization': f'Bearer {HERMES_TOKEN}',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())

        raw = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        match = __import__('re').search(r'\{[\s\S]*\}', raw)
        if not match:
            raise ValueError("No JSON in Hermes response")

        result = json.loads(match.group())
        result['ai_available'] = True
        logger.info(f"AI review: {result['action']} | confidence={result['confidence']} | match={result.get('strategy_match')}")
        return result

    except Exception as e:
        logger.warning(f"Hermes review failed ({e}) — using heuristic")
        return _heuristic_review(signal)


def _heuristic_review(signal: dict) -> dict:
    """Fallback heuristic review when Hermes is unavailable."""
    entry = signal.get('entry_price', 0) or 0
    sl    = signal.get('stop_loss', 0) or 0
    tp    = signal.get('take_profit', 0) or 0
    conf  = signal.get('confidence', 0) or 0

    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    rr     = reward / risk if risk > 0 else 0

    if conf < 0.5 or rr < 1.5:
        return {
            'action':         'reject',
            'confidence':     conf,
            'strategy_match': None,
            'reasoning':      f"Heuristic: confidence {conf:.0%} or R:R {rr:.1f} below threshold.",
            'ai_available':   False
        }

    return {
        'action':         'approve',
        'confidence':     conf,
        'strategy_match': signal.get('strategy_id'),
        'reasoning':      f"Heuristic: confidence {conf:.0%}, R:R {rr:.1f} acceptable.",
        'ai_available':   False
    }
