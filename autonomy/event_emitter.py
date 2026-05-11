"""
Event Emitter.

The single entry point for emitting system_events.
Any service, agent, or worker calls emit_event() to put an event
on the bus. The autonomy_worker polls and dispatches.

Usage:
    from autonomy.event_emitter import emit_event

    emit_event(
        event_type='credit_analysis_completed',
        client_id='client-uuid',
        payload={'score': 720, 'tier': 'A'},
    )
"""

import os
import json
import hashlib
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('EventEmitter')

SUPABASE_URL  = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY  = os.getenv('SUPABASE_KEY', '')
NEXUS_TENANT  = os.getenv('NEXUS_TENANT_ID', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _make_idempotency_key(event_type: str, client_id: Optional[str], payload: dict) -> str:
    """
    Stable hash so re-emitting the same logical event is a no-op.
    Based on: event_type + client_id + sorted payload keys+values.
    """
    raw = f"{event_type}|{client_id}|{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def emit_event(
    event_type: str,
    client_id: Optional[str]       = None,
    payload: Optional[dict]        = None,
    idempotency_key: Optional[str] = None,
    tenant_id: Optional[str]       = None,
) -> Optional[str]:
    """
    Write one system_events row.

    Returns the event id on success, None if the event already exists
    (idempotency hit) or on failure.
    """
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/system_events"
    p   = payload or {}
    idk = idempotency_key or _make_idempotency_key(event_type, client_id, p)

    row = {
        'event_type':      event_type,
        'client_id':       client_id,
        'tenant_id':       tenant_id or os.getenv('NEXUS_TENANT_ID', NEXUS_TENANT),
        'payload':         p,
        'status':          'pending',
        'idempotency_key': idk,
    }

    data = json.dumps(row).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            if rows:
                event_id = rows[0].get('id')
                logger.info(
                    f"Event emitted: {event_type} client={client_id} "
                    f"id={event_id} idk={idk[:8]}…"
                )
                return event_id
            return None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        if '23505' in body or 'unique' in body.lower():
            logger.debug(f"Event deduplicated (idempotency): {event_type} idk={idk[:8]}…")
            return None
        logger.error(f"emit_event({event_type}) → HTTP {e.code}: {body}")
        return None
    except Exception as e:
        logger.error(f"emit_event({event_type}) → {e}")
        return None


def emit_batch(events: list) -> int:
    """
    Emit a list of event dicts, each with keys:
      event_type, client_id (opt), payload (opt), idempotency_key (opt)
    Returns count successfully emitted.
    """
    count = 0
    for ev in events:
        result = emit_event(
            event_type=ev.get('event_type', ''),
            client_id=ev.get('client_id'),
            payload=ev.get('payload'),
            idempotency_key=ev.get('idempotency_key'),
        )
        if result:
            count += 1
    return count
