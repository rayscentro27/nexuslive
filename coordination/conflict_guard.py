"""
Conflict Guard.

Prevents duplicate tasks and repeated messages across agents.
Called before any output_service write when the caller needs
an extra conflict check beyond the standard decision_layer.

Rules:
  1. No two open tasks with the same title for the same client
  2. No repeated message with same content to same client within DEDUP_WINDOW
  3. No agent creates more than MAX_TASKS_PER_CLIENT tasks in 48h
"""

import os
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

logger = logging.getLogger('ConflictGuard')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

MAX_TASKS_PER_CLIENT    = int(os.getenv('CONFLICT_MAX_TASKS_PER_CLIENT', '10'))
MESSAGE_DEDUP_MINUTES   = int(os.getenv('CONFLICT_MESSAGE_DEDUP_MINUTES', '60'))


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


def task_exists(client_id: str, title: str) -> bool:
    """Return True if an open task with this exact title already exists for the client."""
    rows = _sb_get(
        f"client_tasks?user_id=eq.{client_id}"
        f"&title=eq.{urllib.parse.quote(title)}"
        f"&select=id&limit=1"
    )
    return len(rows) > 0


def message_recently_sent(
    client_id: str,
    content_prefix: str,
    minutes: int = MESSAGE_DEDUP_MINUTES,
) -> bool:
    """
    Return True if a message starting with content_prefix was sent
    to this client within the last N minutes.
    Uses ilike for prefix matching.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    safe   = urllib.parse.quote(content_prefix[:50])
    rows   = _sb_get(
        f"internal_messages?client_id=eq.{client_id}"
        f"&content=ilike.{safe}%25"
        f"&created_at=gt.{cutoff}"
        f"&select=id&limit=1"
    )
    return len(rows) > 0


def client_task_limit_reached(client_id: str) -> bool:
    """Return True if client has hit the per-48h task creation limit."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    rows   = _sb_get(
        f"agent_action_history?client_id=eq.{client_id}"
        f"&action_taken=eq.created_task"
        f"&created_at=gt.{cutoff}"
        f"&select=id&limit={MAX_TASKS_PER_CLIENT + 1}"
    )
    return len(rows) >= MAX_TASKS_PER_CLIENT


def check_task(client_id: str, title: str) -> Tuple[bool, str]:
    """
    Returns (ok_to_create, reason).
    ok_to_create=True means safe to proceed.
    """
    if client_task_limit_reached(client_id):
        return False, f'client task limit ({MAX_TASKS_PER_CLIENT}/48h) reached'
    if task_exists(client_id, title):
        return False, f'duplicate task: "{title}" already open for this client'
    return True, 'ok'


def check_message(client_id: str, content: str) -> Tuple[bool, str]:
    """Returns (ok_to_send, reason)."""
    if message_recently_sent(client_id, content[:50]):
        return False, f'duplicate message sent within {MESSAGE_DEDUP_MINUTES}m'
    return True, 'ok'
