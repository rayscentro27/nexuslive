"""
Strategy Candidate Ingest Service.

Converts a research table row into a strategy_candidates staging record.
This is the entry point for the strategy scoring pipeline.

Flow:
  research (source='local' or 'storage:*')
      → ingest_strategy_candidate()
      → strategy_candidates (review_status='new')

Key rules:
  - Idempotent: if a strategy_candidates row already exists for this
    source_research_id the function returns that row's id without a duplicate.
  - strategy_type is inferred from title + content keywords.
  - Raw content is preserved verbatim for audit and re-scoring.

Usage:
  from strategy_candidate_ingest_service import ingest_strategy_candidate
  candidate_id = ingest_strategy_candidate(research_row)
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('StrategyCandidateIngestService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


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


# ─── Strategy type inference ──────────────────────────────────────────────────

_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ('scalping',          ['scalp', '1-minute', '1m chart', 'micro']),
    ('mean_reversion',    ['mean reversion', 'revert', 'oversold', 'overbought', 'rsi', 'bollinger']),
    ('breakout',          ['breakout', 'break out', 'consolidation break', 'range break']),
    ('momentum',          ['momentum', 'rsi divergence', 'macd', 'volume surge', 'parabolic']),
    ('trend_following',   ['trend following', 'moving average', 'ema', 'sma', 'trend continuation']),
    ('pullback',          ['pullback', 'pull back', 'retracement', 'fibonacci', 'fib level']),
    ('reversal',          ['reversal', 'pin bar', 'engulfing', 'double top', 'double bottom', 'head and shoulders']),
    ('range',             ['range trading', 'support and resistance', 'channel', 'horizontal level']),
    ('swing',             ['swing trade', 'swing trading', 'multi-day', 'overnight hold']),
    ('position',          ['position trade', 'long-term', 'weekly chart', 'monthly chart']),
]


def _infer_strategy_type(title: str, content: str) -> str:
    """Deterministic strategy type from keyword matching."""
    text = (title + ' ' + content).lower()
    for strategy_type, keywords in _TYPE_KEYWORDS:
        if any(kw in text for kw in keywords):
            return strategy_type
    return 'general'


# ─── Idempotency check ────────────────────────────────────────────────────────

def _candidate_exists(source_research_id: str) -> Optional[str]:
    """Return existing candidate_id if already ingested, else None."""
    try:
        rows = _sb_get(
            f"strategy_candidates"
            f"?source_research_id=eq.{source_research_id}"
            f"&select=id&limit=1"
        )
        return rows[0]['id'] if rows else None
    except Exception:
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def ingest_strategy_candidate(research_row: dict) -> Optional[str]:
    """
    Convert a research table row into a strategy_candidates row.

    Args:
        research_row: Dict with keys: id, title, content, source, created_at

    Returns:
        UUID of the strategy_candidates row, or None on failure.
    """
    research_id = str(research_row.get('id', ''))
    title       = (research_row.get('title') or '').strip()
    content     = (research_row.get('content') or '').strip()
    source      = research_row.get('source', 'research')

    if not research_id or not title:
        logger.warning("ingest_strategy_candidate: missing id or title — skipping")
        return None

    # Idempotency
    existing = _candidate_exists(research_id)
    if existing:
        logger.info(f"strategy_candidate already exists for research {research_id}: {existing}")
        return existing

    strategy_type = _infer_strategy_type(title, content)

    row = {
        'source_research_id': research_id,
        'source':             source,
        'title':              title[:500],    # guard against runaway titles
        'strategy_type':      strategy_type,
        'raw_content':        content,
        'review_status':      'new',
        'updated_at':         datetime.now(timezone.utc).isoformat(),
        'raw':                json.dumps({'research_row': research_row}),
    }

    try:
        inserted = _sb_insert('strategy_candidates', row)
        candidate_id = inserted.get('id')
        if not candidate_id:
            logger.error(f"Insert returned no id for research {research_id}")
            return None
        logger.info(
            f"Ingested strategy candidate {candidate_id} ← research {research_id} "
            f"({strategy_type}: {title[:60]})"
        )
        return candidate_id
    except Exception as e:
        logger.error(f"Failed to ingest strategy candidate for research {research_id}: {e}")
        return None
