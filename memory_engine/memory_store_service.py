"""
Memory Store Service.

Writes and upserts entries to the ai_memory table.
Used by the memory_worker and any pipeline step that wants to persist
context across sessions.

Memory types:
  client_state         — last known facts about a client (upserted per subject)
  conversation_summary — condensed AI session thread (append-only)
  strategy_history     — notable strategy outcomes and reasoning
  signal_history       — notable signal context and results
  funding_history      — per-client funding advice and decisions
  credit_history       — per-client credit review notes
  communication_history — per-client communication log
  business_setup_history — business setup steps and status
  capital_history      — capital/trading decisions for a client
  grant_history        — grant eligibility and application notes
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('MemoryStore')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

_HEADERS = {
    'apikey':        SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type':  'application/json',
    'Prefer':        'return=representation',
}


def _headers() -> dict:
    """Return fresh headers (SUPABASE_KEY may be set after module load)."""
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
    except urllib.error.HTTPError as e:
        logger.error(f"PATCH {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return False
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

def store_memory(
    memory_type: str,
    content: str,
    subject_id: Optional[str]          = None,
    subject_type: Optional[str]        = None,
    meta: Optional[dict]               = None,
    expires_hours: Optional[int]       = None,
    client_id: Optional[str]           = None,
    tenant_id: Optional[str]           = None,
    source_agent: Optional[str]        = None,
    structured_payload: Optional[dict] = None,
    importance_score: int              = 50,
) -> Optional[str]:
    """
    Append a new memory row. Returns the new row id, or None on failure.
    Use this for conversation_summary, strategy_history, signal_history,
    funding_history, credit_history, communication_history, etc.
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    row: dict = {
        'memory_type':     memory_type,
        'content':         content,
        'subject_id':      subject_id,
        'subject_type':    subject_type,
        'meta':            meta or {},
        'is_active':       True,
        'updated_at':      now.isoformat(),
        'importance_score': importance_score,
    }
    if expires_hours:
        row['expires_at'] = (now + timedelta(hours=expires_hours)).isoformat()
    if client_id:
        row['client_id'] = client_id
    if tenant_id:
        row['tenant_id'] = tenant_id
    if source_agent:
        row['source_agent'] = source_agent
    if structured_payload:
        row['structured_payload'] = structured_payload

    result = _sb_post('ai_memory', row)
    if result:
        logger.info(f"Stored memory [{memory_type}] id={result.get('id')} subject={subject_id}")
        return result.get('id')
    return None


def upsert_memory(
    memory_type: str,
    content: str,
    subject_id: str,
    subject_type: str,
    meta: Optional[dict]               = None,
    expires_hours: Optional[int]       = None,
    client_id: Optional[str]           = None,
    tenant_id: Optional[str]           = None,
    source_agent: Optional[str]        = None,
    structured_payload: Optional[dict] = None,
    importance_score: int              = 50,
) -> Optional[str]:
    """
    Upsert: replace the existing active memory for (memory_type, subject_id,
    subject_type) with new content. Creates if missing.
    Use this for client_state (one live record per entity).
    """
    # Deactivate any existing active rows for this subject+type
    existing = _sb_get(
        f"ai_memory?memory_type=eq.{memory_type}"
        f"&subject_id=eq.{subject_id}"
        f"&subject_type=eq.{subject_type}"
        f"&is_active=eq.true&select=id&limit=20"
    )
    if existing:
        ids = ','.join(f'"{r["id"]}"' for r in existing)
        _sb_patch(
            f"ai_memory?id=in.({ids})",
            {'is_active': False}
        )

    return store_memory(
        memory_type=memory_type,
        content=content,
        subject_id=subject_id,
        subject_type=subject_type,
        meta=meta,
        expires_hours=expires_hours,
        client_id=client_id,
        tenant_id=tenant_id,
        source_agent=source_agent,
        structured_payload=structured_payload,
        importance_score=importance_score,
    )


def update_last_used(memory_id: str) -> bool:
    """
    Bump last_used_at to now for a memory row.
    Call this when a memory is read and used by an agent.
    """
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"ai_memory?id=eq.{memory_id}",
        {'last_used_at': now}
    )


def deactivate_memory(memory_id: str) -> bool:
    """Mark a single memory row as inactive."""
    return _sb_patch(
        f"ai_memory?id=eq.{memory_id}",
        {'is_active': False}
    )


def expire_old_memories(max_age_hours: int = 720) -> int:
    """
    Mark memories older than max_age_hours as inactive (if no explicit
    expires_at was set). Returns count deactivated.
    """
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()

    # Deactivate rows past their explicit expires_at
    rows = _sb_get(
        f"ai_memory?is_active=eq.true"
        f"&expires_at=lt.{cutoff}"
        f"&select=id&limit=500"
    )
    deactivated = 0
    for row in rows:
        if _sb_patch(f"ai_memory?id=eq.{row['id']}", {'is_active': False}):
            deactivated += 1

    if deactivated:
        logger.info(f"Expired {deactivated} ai_memory rows")
    return deactivated
