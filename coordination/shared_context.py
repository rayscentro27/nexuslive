"""
Shared Context.

Reads and writes agent_context — one row per client.
Every agent calls get_context() before deciding, and update_context()
after acting to keep the shared state current.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('SharedContext')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
NEXUS_TENANT = os.getenv('NEXUS_TENANT_ID', '')

# Max recent_events to keep in the jsonb array
MAX_RECENT_EVENTS = 20


def _headers(prefer: str = '') -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    h   = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    if prefer:
        h['Prefer'] = prefer
    return h


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers('return=minimal'), method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=8) as _:
            return True
    except Exception as e:
        logger.warning(f"PATCH {path} → {e}")
        return False


def _sb_post(path: str, body: dict) -> Optional[str]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers('return=representation'), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
            return rows[0].get('id') if rows else None
    except Exception as e:
        logger.warning(f"POST {path} → {e}")
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def get_context(client_id: str) -> dict:
    """
    Return the agent_context row for a client, or a fresh default dict
    if no row exists yet.
    """
    rows = _sb_get(
        f"agent_context?client_id=eq.{client_id}&select=*&limit=1"
    )
    if rows:
        return rows[0]
    return {
        'client_id':      client_id,
        'active_stage':   'discovery',
        'recent_events':  [],
        'last_actions':   {},
        'cooldown_state': {},
        'meta':           {},
    }


def upsert_context(client_id: str, updates: dict) -> bool:
    """
    Upsert the agent_context row.
    PATCH if exists, POST if new.
    """
    now = datetime.now(timezone.utc).isoformat()
    updates['updated_at'] = now

    existing = _sb_get(
        f"agent_context?client_id=eq.{client_id}&select=id&limit=1"
    )
    if existing:
        return _sb_patch(
            f"agent_context?client_id=eq.{client_id}",
            updates,
        )
    else:
        row = {
            'client_id':      client_id,
            'tenant_id':      os.getenv('NEXUS_TENANT_ID', NEXUS_TENANT),
            'active_stage':   updates.get('active_stage', 'discovery'),
            'recent_events':  updates.get('recent_events', []),
            'last_actions':   updates.get('last_actions', {}),
            'cooldown_state': updates.get('cooldown_state', {}),
            'meta':           updates.get('meta', {}),
            'created_at':     now,
            'updated_at':     now,
        }
        return _sb_post('agent_context', row) is not None


def advance_stage(client_id: str, new_stage: str) -> bool:
    """
    Move a client to a new active_stage.
    Stage order: discovery → credit_review → funding → communication → complete
    """
    logger.info(f"Client {client_id} advancing to stage: {new_stage}")
    return upsert_context(client_id, {'active_stage': new_stage})


def record_event_in_context(client_id: str, event_type: str) -> bool:
    """
    Append event_type to recent_events (capped at MAX_RECENT_EVENTS).
    """
    ctx    = get_context(client_id)
    events = ctx.get('recent_events') or []
    if isinstance(events, str):
        try:
            events = json.loads(events)
        except Exception:
            events = []
    events.append(event_type)
    events = events[-MAX_RECENT_EVENTS:]
    return upsert_context(client_id, {'recent_events': events})


def record_agent_action(client_id: str, agent_name: str, action: str) -> bool:
    """
    Update last_actions[agent_name] = {action, timestamp}.
    """
    now    = datetime.now(timezone.utc).isoformat()
    ctx    = get_context(client_id)
    actions = ctx.get('last_actions') or {}
    if isinstance(actions, str):
        try:
            actions = json.loads(actions)
        except Exception:
            actions = {}
    actions[agent_name] = {'action': action, 'at': now}
    return upsert_context(client_id, {'last_actions': actions})


def set_cooldown(client_id: str, agent_name: str, until_iso: str) -> bool:
    """Set a cooldown expiry for an agent for this client."""
    ctx    = get_context(client_id)
    cd     = ctx.get('cooldown_state') or {}
    if isinstance(cd, str):
        try:
            cd = json.loads(cd)
        except Exception:
            cd = {}
    cd[agent_name] = until_iso
    return upsert_context(client_id, {'cooldown_state': cd})


def is_in_cooldown(client_id: str, agent_name: str) -> bool:
    """Return True if agent is currently in cooldown for this client."""
    ctx = get_context(client_id)
    cd  = ctx.get('cooldown_state') or {}
    if isinstance(cd, str):
        try:
            cd = json.loads(cd)
        except Exception:
            return False
    until = cd.get(agent_name)
    if not until:
        return False
    now = datetime.now(timezone.utc).isoformat()
    return until > now
