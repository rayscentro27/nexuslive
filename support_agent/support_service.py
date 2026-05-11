"""
Support Service.

Manages support_threads, support_messages, and support_resolutions.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('SupportService')

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


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
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


def open_thread(
    subject: str,
    category: str,
    client_id: Optional[str] = None,
    lead_id: Optional[str]   = None,
    priority: str            = 'normal',
) -> Optional[dict]:
    now = datetime.now(timezone.utc).isoformat()
    row: dict = {
        'subject':    subject[:200],
        'status':     'open',
        'category':   category,
        'priority':   priority,
        'updated_at': now,
    }
    if client_id:
        row['client_id'] = client_id
    if lead_id:
        row['lead_id'] = lead_id
    return _sb_post('support_threads', row)


def add_message(thread_id: str, sender_role: str, content: str) -> Optional[str]:
    """sender_role: 'client' | 'agent' | 'human_agent'"""
    now = datetime.now(timezone.utc).isoformat()
    result = _sb_post('support_messages', {
        'thread_id':   thread_id,
        'sender_role': sender_role,
        'content':     content,
    })
    _sb_patch(f"support_threads?id=eq.{thread_id}",
              {'status': 'in_progress', 'updated_at': now})
    return result.get('id') if result else None


def resolve_thread(thread_id: str, resolution: str, resolved_by: str = 'ai_agent') -> bool:
    now = datetime.now(timezone.utc).isoformat()
    _sb_post('support_resolutions', {
        'thread_id':   thread_id,
        'resolution':  resolution,
        'resolved_by': resolved_by,
    })
    return _sb_patch(
        f"support_threads?id=eq.{thread_id}",
        {'status': 'resolved', 'resolved_at': now, 'updated_at': now},
    )


def escalate_thread(thread_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"support_threads?id=eq.{thread_id}",
        {'status': 'escalated', 'priority': 'high', 'updated_at': now},
    )


def get_open_threads(limit: int = 50) -> List[dict]:
    return _sb_get(
        f"support_threads?status=in.(open,in_progress)&order=priority.asc,updated_at.asc"
        f"&limit={limit}&select=*"
    )


def get_thread_messages(thread_id: str) -> List[dict]:
    return _sb_get(
        f"support_messages?thread_id=eq.{thread_id}&order=created_at.asc&select=*"
    )
