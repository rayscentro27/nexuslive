"""
Outcome Tracker.

Records outcome events when signals or strategies are approved/rejected/expired.
The optimization worker reads these to adjust scoring weights over time.

event_type values:
  signal_approved   | signal_rejected   | signal_expired
  strategy_approved | strategy_rejected | strategy_expired
  funding_won       | funding_lost

outcome values:
  win | loss | neutral | pending
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('OutcomeTracker')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


# ─── Public API ───────────────────────────────────────────────────────────────

def record_outcome(
    event_type: str,
    outcome: str,
    source_id: Optional[str]    = None,
    source_type: Optional[str]  = None,
    score_at_time: Optional[float] = None,
    notes: Optional[str]        = None,
    meta: Optional[dict]        = None,
) -> Optional[str]:
    """
    Insert one outcome_events row.
    Returns the new row id, or None on failure.
    """
    row = {
        'event_type':    event_type,
        'outcome':       outcome,
        'source_id':     source_id,
        'source_type':   source_type,
        'score_at_time': score_at_time,
        'notes':         notes,
        'meta':          meta or {},
    }
    result = _sb_post('outcome_events', row)
    if result:
        logger.debug(
            f"Outcome recorded: {event_type}/{outcome} source={source_id} "
            f"score={score_at_time}"
        )
        return result.get('id')
    return None


def get_recent_outcomes(
    source_type: Optional[str] = None,
    event_type: Optional[str]  = None,
    days: int = 7,
    limit: int = 200,
) -> List[dict]:
    """
    Return recent outcome_events rows, newest first.
    Filters: source_type (signal|strategy|funding), event_type prefix, lookback days.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    parts  = [
        f'created_at=gt.{cutoff}',
        f'order=created_at.desc',
        f'limit={limit}',
        'select=*',
    ]
    if source_type:
        parts.append(f'source_type=eq.{source_type}')
    if event_type:
        parts.append(f'event_type=eq.{event_type}')

    return _sb_get(f"outcome_events?{'&'.join(parts)}")


def get_approval_stats(source_type: str, days: int = 7) -> dict:
    """
    Return approval/rejection counts and mean score for source_type
    over the last N days.
    """
    rows = get_recent_outcomes(source_type=source_type, days=days, limit=500)
    approved = [r for r in rows if 'approved' in r.get('event_type', '')]
    rejected = [r for r in rows if 'rejected' in r.get('event_type', '')]

    def mean_score(subset):
        scores = [r['score_at_time'] for r in subset if r.get('score_at_time') is not None]
        return round(sum(scores) / len(scores), 2) if scores else None

    total = len(approved) + len(rejected)
    return {
        'total':              total,
        'approved':           len(approved),
        'rejected':           len(rejected),
        'approval_rate':      round(len(approved) / total, 4) if total else None,
        'avg_score_approved': mean_score(approved),
        'avg_score_rejected': mean_score(rejected),
    }
