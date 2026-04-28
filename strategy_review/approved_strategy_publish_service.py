"""
Approved Strategy Publish Service.

Takes an approved strategy_candidate + its score and writes a portal-safe
educational record to approved_strategies.

Responsibilities:
  - Extract or template: summary, when_it_works, when_it_fails, risk_note
  - Set expiry (default 30 days — strategies are evergreen vs signals)
  - Write approved_strategies row with is_published=True

Key guarantees:
  - Candidates NEVER reach the portal — only approved_strategies does.
  - No raw backtest data, no execution instructions in output.
  - Idempotent: skips if an approved_strategies row already exists
    for this candidate_id.

Usage:
  from approved_strategy_publish_service import publish_approved_strategy
  strategy_id = publish_approved_strategy(candidate_id, candidate, score)
"""

import os
import json
import re
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('ApprovedStrategyPublishService')

SUPABASE_URL  = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY  = os.getenv('SUPABASE_KEY', '')

EXPIRY_DAYS   = int(os.getenv('STRATEGY_EXPIRY_DAYS', '30'))


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


# ─── Content extraction helpers ───────────────────────────────────────────────

def _extract_summary(content: str, title: str, max_len: int = 400) -> str:
    """
    Extract or build a plain-English educational summary.
    Uses first substantial paragraph; falls back to first N words.
    """
    if not content:
        return f"This strategy explores {title.lower()} patterns."

    # Try to use the first paragraph (most summaries lead with overview)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content.strip()) if len(p.strip()) > 40]
    if paragraphs:
        para = paragraphs[0]
        # Truncate to max_len at a word boundary
        if len(para) > max_len:
            para = para[:max_len].rsplit(' ', 1)[0] + '…'
        return para

    # Fallback: first max_len chars
    truncated = content[:max_len].rsplit(' ', 1)[0]
    return truncated + '…' if len(content) > max_len else content


def _extract_when_it_works(content: str, strategy_type: Optional[str]) -> str:
    """
    Extract 'when it works' text from content, or use template.
    """
    works_patterns = [
        r'works\s+(?:well|best)\s+(?:in|when|during)[^\n.]{10,120}',
        r'best\s+(?:used|applied|suited)\s+(?:in|when|during|for)[^\n.]{10,120}',
        r'ideal\s+for[^\n.]{10,120}',
        r'performs\s+(?:well|best)[^\n.]{10,120}',
        r'suited\s+for[^\n.]{10,120}',
    ]
    for pattern in works_patterns:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            sentence = m.group(0).strip().capitalize()
            return sentence if sentence.endswith('.') else sentence + '.'

    # Template fallback by strategy type
    templates = {
        'trend_following':  'Works best in strongly trending markets with clear directional bias.',
        'mean_reversion':   'Performs well in ranging markets where price oscillates around a mean.',
        'breakout':         'Most effective during periods of low volatility followed by expansion.',
        'momentum':         'Suited to trending conditions with strong volume confirmation.',
        'pullback':         'Ideal in established trends when price retraces to key support or resistance.',
        'reversal':         'Best applied at significant support/resistance levels with confirmation signals.',
        'scalping':         'Works in high-liquidity sessions with tight spreads and clear price action.',
        'swing':            'Suited to trending or range-bound markets over multi-day holding periods.',
        'range':            'Performs in clearly defined horizontal ranges with reliable boundaries.',
    }
    return templates.get(strategy_type or '', 'Performs best when market conditions align with the strategy\'s core setup requirements.')


def _extract_when_it_fails(content: str, strategy_type: Optional[str]) -> str:
    """
    Extract 'when it fails' text from content, or use template.
    """
    fails_patterns = [
        r'(?:avoid|fails?\s+in|does\s+not\s+work|not\s+suited)[^\n.]{10,120}',
        r'(?:choppy|ranging|low\s+volume|news\s+event)[^\n.]{5,120}',
        r'when\s+to\s+avoid[^\n.]{10,120}',
        r'risks?\s+include[^\n.]{10,120}',
    ]
    for pattern in fails_patterns:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            sentence = m.group(0).strip().capitalize()
            return sentence if sentence.endswith('.') else sentence + '.'

    templates = {
        'trend_following':  'Struggles in choppy, sideways markets where false breakouts are common.',
        'mean_reversion':   'Fails in strongly trending conditions where price does not revert.',
        'breakout':         'Produces false signals in noisy, range-bound markets with no follow-through.',
        'momentum':         'Underperforms in reversing or range-bound conditions after a momentum peak.',
        'pullback':         'Dangerous in counter-trend conditions or when the primary trend has reversed.',
        'reversal':         'High failure rate in strong trending conditions — fighting the trend is costly.',
        'scalping':         'Unfavourable in wide-spread conditions, major news events, or thin liquidity.',
        'swing':            'Struggles when market direction reverses sharply between entry and target.',
        'range':            'Fails when a major catalyst causes a range breakout or breakdown.',
    }
    return templates.get(strategy_type or '', 'Performance degrades when market conditions shift away from the strategy\'s optimal environment.')


def _extract_risk_note(content: str, score: dict) -> str:
    """
    Extract risk note from content, or build from score data.
    """
    risk_patterns = [
        r'risk(?:\s+management|\s+note|\s+warning)?[:\s]+[^\n.]{20,200}',
        r'stop\s+loss[^\n.]{10,120}',
        r'maximum\s+loss[^\n.]{10,120}',
        r'drawdown[^\n.]{10,120}',
    ]
    for pattern in risk_patterns:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            sentence = m.group(0).strip().capitalize()
            # Don't return execution-style instructions
            if not any(w in sentence.lower() for w in ['click', 'press', 'execute now']):
                return sentence if sentence.endswith('.') else sentence + '.'

    notes = score.get('notes', '') or ''
    risk_warnings = []
    if 'no_stop_loss_concept' in notes:
        risk_warnings.append('No explicit stop loss concept was identified — define your own invalidation level before trading.')
    if 'no_risk_management' in notes:
        risk_warnings.append('Risk management details are limited — size positions to risk no more than 1–2% of capital per trade.')
    if risk_warnings:
        return ' '.join(risk_warnings)

    return (
        'Always define your invalidation level (stop loss) before entering any trade. '
        'Risk no more than 1–2% of trading capital per position regardless of signal confidence.'
    )


# ─── Idempotency check ────────────────────────────────────────────────────────

def _published_exists(candidate_id: str) -> Optional[str]:
    try:
        rows = _sb_get(
            f"approved_strategies?candidate_id=eq.{candidate_id}&select=id&limit=1"
        )
        return rows[0]['id'] if rows else None
    except Exception:
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def publish_approved_strategy(
    candidate_id: str,
    candidate: dict,
    score: dict,
) -> Optional[str]:
    """
    Generate and publish an approved_strategies row.
    Idempotent — returns existing id if already published.

    Args:
        candidate_id: UUID of the strategy_candidates row.
        candidate:    The strategy_candidates dict.
        score:        Score dict from strategy_scoring_service.

    Returns:
        UUID of the approved_strategies row, or None on failure.
    """
    existing_id = _published_exists(candidate_id)
    if existing_id:
        logger.info(f"approved_strategies record already exists for candidate {candidate_id}")
        return existing_id

    title         = (candidate.get('title') or 'Untitled Strategy').strip()
    strategy_type = candidate.get('strategy_type')
    content       = candidate.get('raw_content') or ''
    now           = datetime.now(timezone.utc)
    expires_at    = now + timedelta(days=EXPIRY_DAYS)

    summary          = _extract_summary(content, title)
    when_it_works    = _extract_when_it_works(content, strategy_type)
    when_it_fails    = _extract_when_it_fails(content, strategy_type)
    risk_note        = _extract_risk_note(content, score)

    row = {
        'candidate_id':   candidate_id,
        'title':          title,
        'strategy_type':  strategy_type,
        'summary':        summary,
        'when_it_works':  when_it_works,
        'when_it_fails':  when_it_fails,
        'risk_note':      risk_note,
        'difficulty_level': score.get('difficulty_level', 'beginner'),
        'confidence_label': score.get('confidence_label', 'medium'),
        'score_total':    score.get('score_total'),
        'is_published':   True,
        'review_status':  'approved',
        'published_at':   now.isoformat(),
        'expires_at':     expires_at.isoformat(),
        'updated_at':     now.isoformat(),
    }

    try:
        inserted = _sb_insert('approved_strategies', row)
        strategy_id = inserted.get('id')
        if not strategy_id:
            logger.error(f"Insert returned no id for candidate {candidate_id}")
            return None
        logger.info(
            f"Published approved strategy {strategy_id} ← candidate {candidate_id} "
            f"({title[:60]} | conf={score.get('confidence_label')} "
            f"diff={score.get('difficulty_level')} "
            f"expires={expires_at.strftime('%Y-%m-%d')})"
        )
        return strategy_id
    except Exception as e:
        logger.error(f"Failed to publish approved strategy for candidate {candidate_id}: {e}")
        return None
