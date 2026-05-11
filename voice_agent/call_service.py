"""
Call Service.

Manages call_sessions, call_transcripts, and call_outcomes.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('CallService')

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


def open_session(
    call_type: str           = 'inbound',
    channel: str             = 'telegram',
    client_id: Optional[str] = None,
    lead_id: Optional[str]   = None,
    org_id: Optional[str]    = None,
) -> Optional[dict]:
    row: dict = {
        'call_type':  call_type,
        'channel':    channel,
        'status':     'open',
        'started_at': datetime.now(timezone.utc).isoformat(),
    }
    if client_id:
        row['client_id'] = client_id
    if lead_id:
        row['lead_id'] = lead_id
    if org_id:
        row['org_id'] = org_id
    return _sb_post('call_sessions', row)


def close_session(session_id: str, outcome: str, duration_sec: int = 0) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"call_sessions?id=eq.{session_id}",
        {'status': 'completed', 'outcome': outcome,
         'ended_at': now, 'duration_sec': duration_sec},
    )


def add_transcript_turn(
    session_id: str,
    speaker: str,
    content: str,
    turn_order: int,
) -> Optional[str]:
    result = _sb_post('call_transcripts', {
        'session_id': session_id,
        'speaker':    speaker,
        'content':    content,
        'turn_order': turn_order,
    })
    return result.get('id') if result else None


def record_outcome(
    session_id: str,
    outcome_type: str,
    notes: str           = '',
    next_action: str     = '',
    follow_up_at: Optional[str] = None,
) -> Optional[str]:
    row: dict = {
        'session_id':   session_id,
        'outcome_type': outcome_type,
        'notes':        notes,
        'next_action':  next_action,
    }
    if follow_up_at:
        row['follow_up_at'] = follow_up_at
    result = _sb_post('call_outcomes', row)
    return result.get('id') if result else None


def get_session_transcript(session_id: str) -> List[dict]:
    return _sb_get(
        f"call_transcripts?session_id=eq.{session_id}&order=turn_order.asc&select=*"
    )


def get_open_sessions(limit: int = 50) -> List[dict]:
    return _sb_get(
        f"call_sessions?status=in.(open,in_progress)&order=started_at.asc&limit={limit}&select=*"
    )


def get_outcome_stats() -> dict:
    rows = _sb_get("call_outcomes?select=outcome_type&limit=2000")
    counts: dict = {}
    for r in rows:
        t = r.get('outcome_type', 'unknown')
        counts[t] = counts.get(t, 0) + 1
    return counts
