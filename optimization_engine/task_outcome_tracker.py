"""
Task Outcome Tracker.

Records what happened with tasks agents created.
Agents call record_task_outcome() immediately after creating a task.
Status updates (completed/cancelled) happen via a separate process or
by polling client_tasks and calling update_task_status().

Used by optimization_summary_job to measure task completion rates.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('TaskOutcomeTracker')

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

def record_task_outcome(
    agent_name: str,
    client_id: str,
    task_title: str,
    task_id: Optional[str]               = None,
    status: str                          = 'pending',
    resolution_time_hours: Optional[float] = None,
    client_engaged: bool                 = False,
    notes: Optional[str]                 = None,
    meta: Optional[dict]                 = None,
) -> Optional[str]:
    """
    Record an agent-created task for outcome tracking.
    Returns the tracking row id, or None on failure.
    """
    row: dict = {
        'agent_name':    agent_name,
        'client_id':     client_id,
        'task_title':    task_title,
        'status':        status,
        'client_engaged': client_engaged,
        'meta':          meta or {},
    }
    if task_id:
        row['task_id'] = task_id
    if resolution_time_hours is not None:
        row['resolution_time_hours'] = resolution_time_hours
    if notes:
        row['notes'] = notes

    result = _sb_post('task_outcomes', row)
    if result:
        logger.debug(f"Recorded task outcome for [{task_title}] id={result.get('id')}")
        return result.get('id')
    return None


def update_task_status(
    tracking_id: str,
    status: str,
    resolution_time_hours: Optional[float] = None,
    client_engaged: bool = False,
    notes: Optional[str] = None,
) -> bool:
    """Update the outcome status of a tracked task."""
    body: dict = {'status': status, 'client_engaged': client_engaged}
    if resolution_time_hours is not None:
        body['resolution_time_hours'] = resolution_time_hours
    if notes:
        body['notes'] = notes
    return _sb_patch(f"task_outcomes?id=eq.{tracking_id}", body)


def get_completion_rate(agent_name: str, days: int = 7) -> dict:
    """
    Return task completion stats for the given agent over the last N days.
    Returns: {'total': int, 'completed': int, 'pending': int,
              'cancelled': int, 'completion_rate': float}
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows   = _sb_get(
        f"task_outcomes"
        f"?agent_name=eq.{agent_name}"
        f"&created_at=gt.{cutoff}"
        f"&select=status,client_engaged&limit=500"
    )
    total     = len(rows)
    completed = sum(1 for r in rows if r.get('status') == 'completed')
    cancelled = sum(1 for r in rows if r.get('status') == 'cancelled')
    pending   = sum(1 for r in rows if r.get('status') == 'pending')
    engaged   = sum(1 for r in rows if r.get('client_engaged'))
    rate      = round(completed / total, 3) if total > 0 else 0.0
    return {
        'total': total, 'completed': completed,
        'cancelled': cancelled, 'pending': pending,
        'client_engaged': engaged, 'completion_rate': rate, 'days': days,
    }


def get_all_agent_stats(days: int = 7) -> List[dict]:
    """Return per-agent task stats for all agents."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows   = _sb_get(
        f"task_outcomes?created_at=gt.{cutoff}&select=agent_name,status,client_engaged&limit=2000"
    )
    by_agent: dict = {}
    for row in rows:
        a = row.get('agent_name', 'unknown')
        if a not in by_agent:
            by_agent[a] = {'total': 0, 'completed': 0, 'cancelled': 0,
                           'pending': 0, 'client_engaged': 0}
        by_agent[a]['total'] += 1
        s = row.get('status', 'pending')
        if s in by_agent[a]:
            by_agent[a][s] += 1
        if row.get('client_engaged'):
            by_agent[a]['client_engaged'] += 1

    results = []
    for agent, stats in by_agent.items():
        total = stats['total']
        stats['agent_name']      = agent
        stats['completion_rate'] = round(stats['completed'] / total, 3) if total else 0.0
        stats['days']            = days
        results.append(stats)
    return results
