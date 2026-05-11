"""
Approved Signal Publish Service.

Takes an approved signal_candidates row + its score and writes a client-safe
educational record to approved_signals.

Responsibilities:
  - Generate educational content (headline, client_summary, why_it_matters, invalidation_note)
  - Optionally enhance content via Hermes (if available) — non-blocking
  - Set expiry based on timeframe (intraday ≤ 4h → 24h; swing ≥ 1D → 72h)
  - Write approved_signals row with published=true
  - Never expose raw price execution data beyond educational context

Key guarantees:
  - Raw signal candidates NEVER reach the portal — only approved_signals does.
  - price/zone data is editorial context only ("key levels"), not execution instructions.
  - Idempotent: skips if an approved_signals row already exists for this source_signal_id.

Usage:
  from approved_signal_publish_service import publish_approved_signal
  signal_id = publish_approved_signal(candidate_id, candidate, score, ai_review)
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('ApprovedSignalPublishService')

SUPABASE_URL   = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY   = os.getenv('SUPABASE_KEY', '')
HERMES_GATEWAY_URL   = os.getenv('HERMES_GATEWAY_URL', 'http://localhost:8642')
HERMES_TOKEN = os.getenv('HERMES_GATEWAY_TOKEN', '')
HERMES_MODEL = os.getenv('HERMES_MODEL', 'hermes')

# Expiry defaults (hours)
EXPIRY_INTRADAY_H = int(os.getenv('SIGNAL_EXPIRY_INTRADAY_H', '24'))
EXPIRY_SWING_H    = int(os.getenv('SIGNAL_EXPIRY_SWING_H',    '72'))

_SWING_TIMEFRAMES = {'1d', '1w', '1w', '1mo', 'd', 'w'}
_INTRADAY_TIMEFRAMES = {'1m', '3m', '5m', '15m', '30m', '1h', '4h', '1', '3', '5', '15', '30', '60', '240'}


# ─── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _sb_insert(table: str, data: dict) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, method='POST',
        headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type':  'application/json',
            'Prefer':        'return=representation',
        }
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        rows = json.loads(r.read())
        return rows[0] if rows else {}


# ─── Expiry ────────────────────────────────────────────────────────────────────

def _calc_expiry(timeframe: str) -> datetime:
    tf = (timeframe or '').lower().strip()
    hours = EXPIRY_SWING_H if tf in _SWING_TIMEFRAMES else EXPIRY_INTRADAY_H
    return datetime.now(timezone.utc) + timedelta(hours=hours)


# ─── Educational content generation ──────────────────────────────────────────

def _fmt_price(price_val) -> str:
    """Format a price for editorial display."""
    try:
        p = float(price_val or 0)
        if p == 0:
            return 'N/A'
        # Show 5 decimal places for forex (small values), 2 for crypto/equities
        return f"{p:.5f}" if p < 100 else f"{p:,.2f}"
    except Exception:
        return str(price_val or 'N/A')


def _extract_price(zone_val, raw_key: str, raw: dict) -> float:
    """Extract a numeric price from a zone dict or raw_payload fallback."""
    if zone_val:
        if isinstance(zone_val, str):
            try: zone_val = json.loads(zone_val)
            except Exception: zone_val = {}
        if isinstance(zone_val, dict):
            p = float(zone_val.get('price', 0) or 0)
            if p: return p
    return float(raw.get(raw_key, 0) or 0)


def _timeframe_label(tf: str) -> str:
    labels = {
        '1m': '1-minute', '3m': '3-minute', '5m': '5-minute',
        '15m': '15-minute', '30m': '30-minute', '1h': '1-hour',
        '4h': '4-hour', '1D': 'daily', '1W': 'weekly', '1MO': 'monthly',
    }
    return labels.get(tf or '', f"{tf or 'unknown'}")


def _setup_context(setup_type: str) -> str:
    ctx = {
        'breakout':           "Breakouts from consolidation can signal the start of a new trend leg.",
        'reversal':           "Price action reversals at key levels offer high-probability turning points.",
        'trend_continuation': "Continuation setups align with the dominant trend, offering lower-risk entries.",
        'pullback':           "Pullbacks to support/resistance provide favorable entries in trending markets.",
        'momentum':           "Momentum signals can capture rapid moves when volume confirms the direction.",
        'range':              "Range setups exploit well-defined support and resistance boundaries.",
        'support_bounce':     "Support bounces position at historically significant demand zones.",
        'resistance_reject':  "Resistance rejections occur when price fails to break through supply zones.",
        'inside_bar':         "Inside bars signal a period of consolidation often preceding a sharp move.",
        'engulfing':          "Engulfing candles show a decisive shift in short-term market sentiment.",
        'pin_bar':            "Pin bars indicate rejection of a price level, often signalling a reversal.",
        'fakeout':            "Fakeouts occur when price briefly breaks a level then reverses sharply.",
        'momentum':           "Momentum setups ride sustained directional pressure with volume confirmation.",
    }
    return ctx.get((setup_type or '').lower(), "This setup aligns with technical analysis principles.")


def _generate_template_content(candidate: dict, score: dict, ai_review: dict) -> dict:
    """
    Build educational content using deterministic templates.
    Does NOT call any external AI — safe as fallback.
    """
    symbol      = (candidate.get('symbol') or 'UNKNOWN').upper()
    direction   = (candidate.get('direction') or 'unknown').lower()
    timeframe   = candidate.get('timeframe') or 'unknown'
    setup_type  = (candidate.get('setup_type') or 'setup').replace('_', ' ')
    market_type = (candidate.get('market_type') or 'market')
    conf_label  = score.get('confidence_label', 'medium')
    risk_label  = score.get('risk_label', 'medium')
    rr_ratio    = score.get('rr_ratio', 0)
    strategy    = ai_review.get('strategy_match') if ai_review else None

    raw = candidate.get('raw_payload') or {}
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except Exception: raw = {}

    entry_price = _extract_price(candidate.get('entry_zone'),  'entry_price', raw)
    stop_price  = _extract_price(candidate.get('stop_zone'),   'stop_loss',   raw)
    target_price = _extract_price(candidate.get('target_zone'), 'take_profit', raw)

    direction_word = 'bullish' if direction == 'long' else 'bearish' if direction == 'short' else direction
    tf_label       = _timeframe_label(timeframe)

    # Headline — max ~80 chars
    headline = (
        f"{symbol} {direction_word.upper()} | "
        f"{setup_type.title()} | "
        f"{timeframe} | "
        f"{conf_label.title()} Conf"
    )[:80]

    # client_summary — 2-3 sentences
    entry_str  = _fmt_price(entry_price)  if entry_price  else "TBD"
    stop_str   = _fmt_price(stop_price)   if stop_price   else "TBD"
    target_str = _fmt_price(target_price) if target_price else "TBD"

    summary_parts = [
        f"{symbol} is showing a {direction_word} {setup_type} pattern on the {tf_label} chart.",
        f"Key levels to watch: entry near {entry_str}, invalidation zone near {stop_str}, "
        f"and a potential target near {target_str}.",
    ]
    if rr_ratio >= 1.5:
        summary_parts.append(
            f"The risk-to-reward profile is approximately 1:{rr_ratio:.1f}, "
            f"which meets the minimum threshold for {conf_label}-confidence educational consideration."
        )
    if strategy:
        summary_parts.append(f"This setup shows overlap with the '{strategy}' research theme.")

    client_summary = " ".join(summary_parts)

    # why_it_matters
    why_it_matters = _setup_context(candidate.get('setup_type'))

    # invalidation_note
    if stop_price:
        inv_direction = "below" if direction == 'long' else "above"
        invalidation_note = (
            f"This setup becomes invalid if price closes {inv_direction} {stop_str} "
            f"on the {tf_label} chart, or if the signal expires without the pattern triggering."
        )
    else:
        invalidation_note = (
            "No specific stop level provided. Monitor for a meaningful close against "
            "the directional bias to invalidate."
        )

    return {
        'headline':          headline,
        'client_summary':    client_summary,
        'why_it_matters':    why_it_matters,
        'invalidation_note': invalidation_note,
    }


def _enhance_with_hermes(
    candidate: dict,
    score: dict,
    ai_review: dict,
    template_content: dict,
) -> dict:
    """
    Optionally call Hermes to generate richer educational text.
    Falls back to template_content silently if unavailable or if it times out.
    """
    if not HERMES_TOKEN:
        return template_content

    symbol      = candidate.get('symbol', 'UNKNOWN')
    direction   = candidate.get('direction', 'unknown')
    setup_type  = candidate.get('setup_type', 'setup')
    timeframe   = candidate.get('timeframe', 'unknown')
    conf_label  = score.get('confidence_label', 'medium')
    rr_ratio    = score.get('rr_ratio', 0)

    prompt = f"""You are writing educational trading commentary for a client portal.
The portal is educational only — no execution instructions.

Signal context:
- Symbol: {symbol}
- Direction: {direction}
- Setup type: {setup_type}
- Timeframe: {timeframe}
- Confidence: {conf_label}
- R:R ratio: {rr_ratio:.1f}
- Strategy match: {ai_review.get('strategy_match') if ai_review else 'none'}

Write a short educational summary (3-4 sentences max). Explain:
1. What the setup is
2. What key levels to watch (entry zone, invalidation zone, target zone)
3. Why this pattern is noteworthy

Rules:
- Write in plain English for a retail investor audience
- Do NOT give trade execution instructions
- Do NOT say "buy" or "sell" — use "bullish opportunity" / "bearish scenario"
- Keep it under 100 words
- Respond with ONLY the summary text, no JSON, no labels

Template to improve: {template_content['client_summary']}"""

    try:
        body = json.dumps({
            'model':       HERMES_MODEL,
            'messages':    [{'role': 'user', 'content': prompt}],
            'temperature': 0.4,
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
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        enhanced = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        if enhanced and len(enhanced) > 30:
            logger.info(f"Hermes enhanced summary for {symbol}")
            return {**template_content, 'client_summary': enhanced}
    except Exception as e:
        logger.warning(f"Hermes enhancement skipped ({e}) — using template")

    return template_content


# ─── Idempotency check ────────────────────────────────────────────────────────

def _published_exists(candidate_id: str) -> bool:
    try:
        rows = _sb_get(
            f"approved_signals?candidate_id=eq.{candidate_id}&select=id&limit=1"
        )
        return len(rows) > 0
    except Exception:
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def publish_approved_signal(
    candidate_id: str,
    candidate: dict,
    score: dict,
    ai_review: dict,
    tenant_id: str = None,
) -> Optional[str]:
    """
    Generate an educational signal record and publish it to approved_signals.

    Args:
        candidate_id: UUID of the signal_candidates row.
        candidate:    The signal_candidates dict.
        score:        Score dict from signal_scoring_service.
        ai_review:    AI review dict from signal_reviewer.
        tenant_id:    Optional tenant UUID.

    Returns:
        UUID of the approved_signals row, or None on failure.
    """
    symbol = (candidate.get('symbol') or 'UNKNOWN').upper()

    # Idempotency — check by candidate_id
    if _published_exists(candidate_id):
        logger.info(f"approved_signals record already exists for candidate {candidate_id}")
        return None

    # Generate content
    template = _generate_template_content(candidate, score, ai_review)
    content  = _enhance_with_hermes(candidate, score, ai_review, template)

    now       = datetime.now(timezone.utc)
    expires_at = _calc_expiry(candidate.get('timeframe'))

    DEFAULT_TENANT = os.getenv('NEXUS_TENANT_ID', '00000000-0000-0000-0000-000000000000')

    row = {
        'tenant_id':         DEFAULT_TENANT,
        'candidate_id':      candidate_id,
        'symbol':            symbol,
        'market_type':       candidate.get('market_type'),
        'setup_type':        candidate.get('setup_type'),
        'direction':         candidate.get('direction'),
        'timeframe':         candidate.get('timeframe'),
        'headline':          content['headline'],
        'client_summary':    content['client_summary'],
        'why_it_matters':    content['why_it_matters'],
        'invalidation_note': content['invalidation_note'],
        'confidence_label':  score.get('confidence_label'),
        'risk_label':        score.get('risk_label'),
        'score_total':       score.get('score_total'),
        'is_published':      True,
        'published_at':      now.isoformat(),
        'expires_at':        expires_at.isoformat(),
        'review_status':     'approved',
        'updated_at':        now.isoformat(),
    }
    if tenant_id:
        row['tenant_id'] = tenant_id

    try:
        inserted = _sb_insert('approved_signals', row)
        signal_id = inserted.get('id')
        if not signal_id:
            logger.error(f"Insert returned no id for candidate {candidate_id}")
            return None
        logger.info(
            f"Published approved signal {signal_id} ← candidate {candidate_id} "
            f"({symbol} {candidate.get('direction')} | conf={score.get('confidence_label')} "
            f"expires={expires_at.strftime('%Y-%m-%d %H:%M')} UTC)"
        )
        return signal_id
    except Exception as e:
        logger.error(f"Failed to publish approved signal for candidate {candidate_id}: {e}")
        return None
