"""
Recommendation Tracker.

Records what agents recommended and what happened as a result.
Used by funding_agent and communication_agent after each action.
The optimization_summary_job reads these to measure effectiveness.

Usage:
    rec_id = record_recommendation(
        agent_name='funding_agent',
        client_id=client_id,
        recommendation='created_funding_task',
        score_at_time=score,
    )
    # Later, when outcome is known:
    update_outcome(rec_id, 'accepted')
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('RecommendationTracker')

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


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = 'return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"PATCH {path} → {e}")
        return False


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

def record_recommendation(
    agent_name: str,
    client_id: str,
    recommendation: str,
    outcome: str              = 'pending',
    event_id: Optional[str]  = None,
    score_at_time: Optional[float] = None,
    notes: Optional[str]     = None,
    meta: Optional[dict]     = None,
) -> Optional[str]:
    """
    Record a new recommendation event.
    Returns the row id, or None on failure.
    """
    row: dict = {
        'agent_name':     agent_name,
        'client_id':      client_id,
        'recommendation': recommendation,
        'outcome':        outcome,
        'meta':           meta or {},
    }
    if event_id:
        row['event_id'] = event_id
    if score_at_time is not None:
        row['score_at_time'] = score_at_time
    if notes:
        row['notes'] = notes

    result = _sb_post('recommendation_outcomes', row)
    if result:
        logger.debug(f"Recorded recommendation [{recommendation}] id={result.get('id')}")
        return result.get('id')
    return None


def update_outcome(rec_id: str, outcome: str, notes: Optional[str] = None) -> bool:
    """Update the outcome of a previously recorded recommendation."""
    body: dict = {'outcome': outcome}
    if notes:
        body['notes'] = notes
    return _sb_patch(f"recommendation_outcomes?id=eq.{rec_id}", body)


def get_agent_effectiveness(agent_name: str, days: int = 30) -> dict:
    """
    Return acceptance stats for a given agent over the last N days.
    Returns: {'total': int, 'accepted': int, 'rejected': int,
              'pending': int, 'acceptance_rate': float}
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows   = _sb_get(
        f"recommendation_outcomes"
        f"?agent_name=eq.{agent_name}"
        f"&created_at=gt.{cutoff}"
        f"&select=outcome&limit=500"
    )
    total    = len(rows)
    accepted = sum(1 for r in rows if r.get('outcome') == 'accepted')
    rejected = sum(1 for r in rows if r.get('outcome') == 'rejected')
    pending  = sum(1 for r in rows if r.get('outcome') == 'pending')
    rate     = round(accepted / total, 3) if total > 0 else 0.0
    return {
        'total': total, 'accepted': accepted,
        'rejected': rejected, 'pending': pending,
        'acceptance_rate': rate, 'days': days,
    }


def get_recent_recommendations(
    agent_name: Optional[str] = None,
    client_id: Optional[str]  = None,
    days: int = 7,
    limit: int = 50,
) -> List[dict]:
    """Return recent recommendation rows, optionally filtered."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    parts  = [
        f'created_at=gt.{cutoff}',
        f'order=created_at.desc',
        f'limit={limit}',
        'select=*',
    ]
    if agent_name:
        parts.append(f'agent_name=eq.{agent_name}')
    if client_id:
        parts.append(f'client_id=eq.{client_id}')
    return _sb_get(f"recommendation_outcomes?{'&'.join(parts)}")
