"""
hermes/trade_reviewer.py — AI signal review via an OpenAI-compatible gateway.

Every incoming trade signal passes through Hermes before execution.
Returns approve/reject + confidence + reasoning.
Logs audit rows to hermes_reviews (domain='trading').

Fail-safe: if the configured AI gateway is unreachable, defaults to approve so the
engine never gets silently blocked by an AI outage.
"""

import os
import json
import re
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def _trim_slash(value: str) -> str:
    return str(value or '').rstrip('/')


GATEWAY_BASE_URL = (
    os.getenv('NEXUS_LLM_BASE_URL')
    or os.getenv('OPENROUTER_BASE_URL')
    or os.getenv('OPENAI_BASE_URL')
    or 'https://openrouter.ai/api/v1'
)
GATEWAY_TOKEN = (
    os.getenv('NEXUS_LLM_API_KEY')
    or os.getenv('OPENROUTER_API_KEY')
    or os.getenv('OPENAI_API_KEY')
    or ''
)
GATEWAY_MODEL = (
    os.getenv('NEXUS_LLM_MODEL')
    or os.getenv('OPENROUTER_MODEL')
    or os.getenv('OPENAI_MODEL')
    or 'meta-llama/llama-3.3-70b-instruct'
)
_root = _trim_slash(GATEWAY_BASE_URL)
CHAT_COMPLETIONS_URL = (
    f'{_root}/chat/completions'
    if _root.endswith('/v1') or _root.endswith('/api/v1')
    else f'{_root}/v1/chat/completions'
)
SUPABASE_URL   = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY   = os.getenv('SUPABASE_KEY', '')

# Block signals with Hermes confidence below this threshold
MIN_CONFIDENCE = int(os.getenv('HERMES_MIN_CONFIDENCE', '50'))
REVIEW_TIMEOUT = int(os.getenv('HERMES_REVIEW_TIMEOUT', '8'))

SYSTEM_PROMPT = """\
You are Hermes, AI trading risk officer for the Nexus system. Review every
inbound trade signal and determine whether it should be executed on Oanda.

APPROVED INSTRUMENTS: EURUSD, GBPUSD, USDJPY only. Reject anything else.
APPROVED TIMEFRAMES: H1, H4 only. Reject anything else.
BROKER: Oanda practice account. Max 5 trades/day. Max 0.01 lot per trade.

HARD BLOCKS (auto-reject, no exceptions):
- Reward:Risk ratio < 1.5
- Stop loss not set
- Take profit not set
- Signal confidence < 40%
- Instrument not in approved list

APPROVAL THRESHOLD:
- R:R >= 2.0, confidence >= 60% → approve
- R:R 1.5-1.9 or confidence 40-59% → use judgment, lean toward skip

RISK FLAGS TO NOTE (do not auto-reject, but include in risk_notes):
- Entry near major round number (1.1000, 1.1500, etc.)
- Stop loss < 20 pips (too tight, noise risk)
- Take profit > 200 pips on H1/H4 (overextended target)

Respond with valid JSON only — no prose, no markdown fences.\
"""


# ── AI gateway call ────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> str | None:
    headers = {'Content-Type': 'application/json'}
    if GATEWAY_TOKEN:
        headers['Authorization'] = f'Bearer {GATEWAY_TOKEN}'
    try:
        r = requests.post(
            CHAT_COMPLETIONS_URL,
            headers=headers,
            json={
                'model': GATEWAY_MODEL,
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user',   'content': prompt},
                ],
                'max_tokens': 350,
                'temperature': 0.2,
            },
            timeout=REVIEW_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"AI gateway call failed: {e}")
        return None


def _extract_json(text: str) -> dict | None:
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return None


# ── Supabase audit log ────────────────────────────────────────────────────────

def _log_review(signal: dict, result: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        requests.post(
            f'{SUPABASE_URL}/rest/v1/hermes_reviews',
            headers={
                'apikey':        SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type':  'application/json',
                'Prefer':        'return=minimal',
            },
            json={
                'domain':               'trading',
                'entity_type':          'trade_signal',
                'entity_id':            signal.get('symbol', 'unknown'),
                'review_score':         result.get('confidence', 0),
                'recommendations_json': result,
                'created_at':           datetime.now(timezone.utc).isoformat(),
            },
            timeout=10,
        )
    except Exception as e:
        logger.debug(f"hermes_reviews log failed: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def review_signal(signal: dict) -> dict:
    """
    Review a trade signal with Hermes AI via the configured AI gateway.

    Args:
        signal: dict with symbol, action, entry_price, stop_loss,
                take_profit, timeframe, confidence, source

    Returns:
        dict: {
            approved:       bool,
            confidence:     0–100,
            reason:         str,
            risk_notes:     str,
            recommendation: 'execute' | 'skip' | 'wait'
        }
    """
    symbol    = signal.get('symbol', '?')
    action    = signal.get('action', '?').upper()
    entry     = signal.get('entry_price', '?')
    sl        = signal.get('stop_loss', 'not set')
    tp        = signal.get('take_profit', 'not set')
    timeframe = signal.get('timeframe', '?')
    source    = signal.get('source', 'unknown')
    sig_conf  = signal.get('confidence', 50)

    try:
        rr = round(abs(float(tp) - float(entry)) / abs(float(entry) - float(sl)), 2)
    except Exception:
        rr = 'unknown'

    prompt = f"""Review this trade signal and return JSON only.

Signal details:
  Symbol:      {symbol}
  Action:      {action}
  Entry:       {entry}
  Stop Loss:   {sl}
  Take Profit: {tp}
  R:R Ratio:   {rr}
  Timeframe:   {timeframe}
  Source:      {source}
  Confidence:  {sig_conf}%

Criteria: minimum 2.0 R:R, clear stop placement, coherent direction.

Return exactly:
{{
  "approved": true or false,
  "confidence": 0-100,
  "reason": "one sentence",
  "risk_notes": "brief risk observation",
  "recommendation": "execute" or "skip" or "wait"
}}"""

    logger.info(f"Hermes reviewing: {symbol} {action}")
    raw = _call_llm(prompt)

    if not raw:
        logger.warning("Hermes AI unavailable — defaulting to approve (fail-safe)")
        return {
            'approved': True, 'confidence': 50,
            'reason': 'AI review unavailable — fail-safe approve',
            'risk_notes': '', 'recommendation': 'execute',
        }

    result = _extract_json(raw)
    if not result:
        logger.warning(f"Hermes returned unparseable response: {raw[:120]}")
        return {
            'approved': True, 'confidence': 50,
            'reason': 'AI response unparseable — fail-safe approve',
            'risk_notes': '', 'recommendation': 'execute',
        }

    # Enforce minimum confidence gate
    if result.get('confidence', 100) < MIN_CONFIDENCE:
        result['approved'] = False
        if result.get('recommendation') == 'execute':
            result['recommendation'] = 'skip'

    _log_review(signal, result)
    logger.info(
        f"Hermes verdict: {symbol} {action} → "
        f"{'APPROVED' if result.get('approved') else 'REJECTED'} "
        f"conf={result.get('confidence')} rec={result.get('recommendation')}"
    )
    return result
