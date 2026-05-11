"""
Action History.

Query helpers for agent_action_history.
Used by decision_layer (cooldown/dedup) and coordination_worker (observability).
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('ActionHistory')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {'apikey': key, 'Authorization': f'Bearer {key}'}


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return []


def get_last_action(agent_name: str, client_id: str) -> Optional[dict]:
    """Return the most recent action by this agent for this client."""
    rows = _sb_get(
        f"agent_action_history?agent_name=eq.{agent_name}"
        f"&client_id=eq.{client_id}"
        f"&order=created_at.desc&limit=1&select=*"
    )
    return rows[0] if rows else None


def get_recent_actions(
    agent_name: Optional[str] = None,
    client_id: Optional[str]  = None,
    hours: int = 24,
    limit: int = 100,
) -> List[dict]:
    """Return recent actions, optionally filtered by agent or client."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    parts  = [f'created_at=gt.{cutoff}', f'order=created_at.desc', f'limit={limit}', 'select=*']
    if agent_name:
        parts.append(f'agent_name=eq.{agent_name}')
    if client_id:
        parts.append(f'client_id=eq.{client_id}')
    return _sb_get(f"agent_action_history?{'&'.join(parts)}")


def get_action_summary(hours: int = 24) -> dict:
    """
    Return counts grouped by agent_name and action_taken for the last N hours.
    Useful for observability dashboard.
    """
    rows  = get_recent_actions(hours=hours, limit=2000)
    by_agent: dict  = {}
    by_action: dict = {}
    for row in rows:
        a  = row.get('agent_name', 'unknown')
        ac = row.get('action_taken', 'unknown')
        by_agent[a]   = by_agent.get(a, 0)   + 1
        by_action[ac] = by_action.get(ac, 0) + 1
    return {
        'total':     len(rows),
        'by_agent':  by_agent,
        'by_action': by_action,
        'hours':     hours,
    }


def count_active_tasks_for_client(client_id: str, hours: int = 48) -> int:
    """Count how many tasks agents have created for this client recently."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows   = _sb_get(
        f"agent_action_history?client_id=eq.{client_id}"
        f"&action_taken=eq.created_task"
        f"&created_at=gt.{cutoff}"
        f"&select=id&limit=200"
    )
    return len(rows)
