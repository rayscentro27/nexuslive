"""
Output Service.

The ONLY way agents write external outputs. Agents call these functions;
this service handles Supabase writes with idempotency.

Outputs:
  1. client_tasks    — visible task in the CRM (AFinalChapter)
  2. internal_messages — agent-to-agent coordination
  3. agent_action_history — audit log of every agent decision
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('OutputService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
NEXUS_TENANT = os.getenv('NEXUS_TENANT_ID', '')


def _headers(prefer: str = 'return=representation') -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        prefer,
    }


def _sb_post(table: str, row: dict) -> Optional[str]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{table}"
    data = json.dumps(row).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0].get('id') if rows else None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        logger.error(f"POST {table} → HTTP {e.code}: {body}")
        return None
    except Exception as e:
        logger.error(f"POST {table} → {e}")
        return None


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers(''))
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return []


# ─── 1. Client Tasks ─────────────────────────────────────────────────────────

def create_task(
    title: str,
    client_id: str,
    agent_name: str,
    description: Optional[str]  = None,
    priority: str               = 'medium',
    task_category: str          = 'autonomy',
    task_type: str              = 'agent_generated',
    meta: Optional[dict]        = None,
) -> Optional[str]:
    """
    Write one row to client_tasks (existing AFinalChapter table).
    Checks for an open duplicate task with same title + client before inserting.
    Returns the task id or None.
    """
    tenant = os.getenv('NEXUS_TENANT_ID', NEXUS_TENANT)

    # Dedup: don't create if same title + client already has an open task
    existing = _sb_get(
        f"client_tasks?user_id=eq.{client_id}"
        f"&title=eq.{urllib.parse.quote(title)}"
        f"&status=neq.completed&status=neq.dismissed"
        f"&select=id&limit=1"
    )
    if existing:
        logger.debug(f"Duplicate task skipped: '{title}' for client {client_id}")
        return existing[0].get('id')

    row = {
        'tenant_id':     tenant,
        'user_id':       client_id,
        'title':         title,
        'description':   description or '',
        'status':        'pending',
        'priority':      priority,
        'task_category': task_category,
        'type':          task_type,
        'assignee_agent': agent_name,
        'metadata':      {**(meta or {}), 'created_by': agent_name},
    }

    task_id = _sb_post('client_tasks', row)
    if task_id:
        logger.info(f"Task created: '{title}' for client {client_id} by {agent_name}")
    return task_id


# ─── 2. Internal Messages ─────────────────────────────────────────────────────

def send_message(
    from_agent: str,
    content: str,
    client_id: Optional[str]   = None,
    to_agent: Optional[str]    = None,
    message_type: str          = 'notification',
    payload: Optional[dict]    = None,
    thread_id: Optional[str]   = None,
) -> Optional[str]:
    """
    Write one row to internal_messages.
    Returns the message id or None.
    """
    tenant = os.getenv('NEXUS_TENANT_ID', NEXUS_TENANT)
    row    = {
        'from_agent':   from_agent,
        'to_agent':     to_agent,
        'client_id':    client_id,
        'tenant_id':    tenant,
        'message_type': message_type,
        'content':      content[:2000],
        'payload':      payload or {},
        'status':       'pending',
        'thread_id':    thread_id,
    }
    msg_id = _sb_post('internal_messages', row)
    if msg_id:
        logger.info(
            f"Message sent: {from_agent}→{to_agent or 'broadcast'} "
            f"type={message_type} client={client_id}"
        )
    return msg_id


# ─── 3. Audit Log ────────────────────────────────────────────────────────────

def log_action(
    agent_name: str,
    action_taken: str,
    client_id: Optional[str]      = None,
    event_id: Optional[str]       = None,
    event_type: Optional[str]     = None,
    output_id: Optional[str]      = None,
    decision_reason: Optional[str] = None,
    meta: Optional[dict]          = None,
) -> Optional[str]:
    """
    Write one row to agent_action_history. Always called — both for
    actions taken and for skipped decisions.
    """
    tenant = os.getenv('NEXUS_TENANT_ID', NEXUS_TENANT)
    row    = {
        'agent_name':      agent_name,
        'client_id':       client_id,
        'tenant_id':       tenant,
        'event_id':        event_id,
        'event_type':      event_type,
        'action_taken':    action_taken,
        'output_id':       output_id,
        'decision_reason': decision_reason,
        'meta':            meta or {},
    }
    return _sb_post('agent_action_history', row)


# urllib.parse needed for query-string escaping in dedup check
import urllib.parse
