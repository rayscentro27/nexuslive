"""
Sales Conversation Service.

Manages lead_profiles, sales_conversations, and conversion_events in Supabase.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('ConversationService')

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
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return None
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


# ─── Lead Profiles ────────────────────────────────────────────────────────────

def get_or_create_lead(
    external_id: str,
    channel: str     = 'telegram',
    name: str        = '',
    interest: str    = '',
) -> dict:
    """Return existing lead or create a new one."""
    import urllib.parse
    rows = _sb_get(
        f"lead_profiles?external_id=eq.{urllib.parse.quote(external_id)}"
        f"&channel=eq.{channel}&select=*&limit=1"
    )
    if rows:
        return rows[0]
    now = datetime.now(timezone.utc).isoformat()
    row = {
        'external_id':  external_id,
        'channel':      channel,
        'name':         name or external_id[:30],
        'interest':     interest,
        'status':       'new',
        'updated_at':   now,
    }
    result = _sb_post('lead_profiles', row)
    return result or row


def update_lead_status(lead_id: str, status: str, notes: str = '') -> bool:
    now  = datetime.now(timezone.utc).isoformat()
    body: dict = {'status': status, 'updated_at': now}
    if notes:
        body['notes'] = notes
    return _sb_patch(f"lead_profiles?id=eq.{lead_id}", body)


def update_lead_interest(lead_id: str, interest: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(f"lead_profiles?id=eq.{lead_id}",
                     {'interest': interest, 'updated_at': now})


# ─── Conversations ────────────────────────────────────────────────────────────

def get_or_create_conversation(
    lead_id: Optional[str]   = None,
    client_id: Optional[str] = None,
    channel: str             = 'telegram',
) -> dict:
    """Return open conversation or create a new one."""
    if lead_id:
        rows = _sb_get(
            f"sales_conversations?lead_id=eq.{lead_id}&status=eq.active&select=*&limit=1"
        )
    elif client_id:
        rows = _sb_get(
            f"sales_conversations?client_id=eq.{client_id}&status=eq.active&select=*&limit=1"
        )
    else:
        rows = []

    if rows:
        return rows[0]

    row: dict = {'channel': channel, 'status': 'active', 'message_count': 0}
    if lead_id:
        row['lead_id'] = lead_id
    if client_id:
        row['client_id'] = client_id
    result = _sb_post('sales_conversations', row)
    return result or row


def increment_message_count(conversation_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    # Fetch current count first
    rows = _sb_get(f"sales_conversations?id=eq.{conversation_id}&select=message_count&limit=1")
    current = rows[0].get('message_count', 0) if rows else 0
    return _sb_patch(
        f"sales_conversations?id=eq.{conversation_id}",
        {'message_count': current + 1, 'last_message_at': now},
    )


def update_conversation_intent(conversation_id: str, intent: str) -> bool:
    return _sb_patch(
        f"sales_conversations?id=eq.{conversation_id}",
        {'intent': intent},
    )


def close_conversation(conversation_id: str, status: str = 'closed') -> bool:
    now = datetime.now(timezone.utc).isoformat()
    body: dict = {'status': status}
    if status == 'converted':
        body['converted_at'] = now
    return _sb_patch(f"sales_conversations?id=eq.{conversation_id}", body)


# ─── Conversion Events ────────────────────────────────────────────────────────

def record_conversion_event(
    event_type: str,
    lead_id: Optional[str]   = None,
    client_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    row: dict = {
        'event_type': event_type,
        'metadata':   metadata or {},
    }
    if lead_id:
        row['lead_id'] = lead_id
    if client_id:
        row['client_id'] = client_id
    result = _sb_post('conversion_events', row)
    return result.get('id') if result else None


def get_conversion_funnel_counts() -> dict:
    """Return counts per conversion event type."""
    rows = _sb_get("conversion_events?select=event_type&limit=1000")
    counts: dict = {}
    for r in rows:
        t = r.get('event_type', 'unknown')
        counts[t] = counts.get(t, 0) + 1
    return counts
