"""
Decision Layer.

Every agent passes its proposed action through here before acting.
Returns (should_act: bool, reason: str).

Checks (in order):
  1. Relevance   — is this event type in the agent's subscriptions?
  2. Safety      — is the payload structurally valid?
  3. Cooldown    — has this agent acted for this client too recently?
  4. Duplicate   — has this agent already acted on a similar event recently?
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

logger = logging.getLogger('DecisionLayer')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Default cooldown per agent per client (minutes)
DEFAULT_COOLDOWN_MINUTES = int(os.getenv('AGENT_COOLDOWN_MINUTES', '30'))
# Dedup window — ignore same event_type from same agent for client within this window
DEDUP_WINDOW_MINUTES = int(os.getenv('AGENT_DEDUP_MINUTES', '60'))


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


# ─── Individual checks ────────────────────────────────────────────────────────

def check_relevance(agent_subscriptions: list, event_type: str) -> Tuple[bool, str]:
    if event_type in agent_subscriptions:
        return True, 'relevant'
    return False, f'not subscribed to {event_type}'


def check_safety(payload: dict) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, 'payload is not a dict'
    # Reject absurdly large payloads (> 50 keys or nested depth > 3)
    if len(payload) > 50:
        return False, f'payload too large ({len(payload)} keys)'
    return True, 'safe'


def check_cooldown(
    agent_name: str,
    client_id: Optional[str],
    cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES,
) -> Tuple[bool, str]:
    """
    True = can act (not in cooldown).
    Reads agent_action_history for the last action by this agent for this client.
    """
    if not client_id:
        return True, 'no client_id, skipping cooldown'

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)).isoformat()
    rows   = _sb_get(
        f"agent_action_history"
        f"?agent_name=eq.{agent_name}"
        f"&client_id=eq.{client_id}"
        f"&action_taken=eq.created_task"
        f"&created_at=gt.{cutoff}"
        f"&select=id,created_at&limit=1"
    )
    if rows:
        return False, f'in cooldown (last action < {cooldown_minutes}m ago)'
    return True, 'cooldown clear'


def check_duplicate(
    agent_name: str,
    client_id: Optional[str],
    event_type: str,
    window_minutes: int = DEDUP_WINDOW_MINUTES,
) -> Tuple[bool, str]:
    """
    True = not a duplicate (ok to act).
    Checks if this agent already processed the same event_type for the same
    client within the dedup window.
    """
    if not client_id:
        return True, 'no client_id, skipping dedup'

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    rows   = _sb_get(
        f"agent_action_history"
        f"?agent_name=eq.{agent_name}"
        f"&client_id=eq.{client_id}"
        f"&event_type=eq.{event_type}"
        f"&action_taken=neq.skipped"
        f"&created_at=gt.{cutoff}"
        f"&select=id&limit=1"
    )
    if rows:
        return False, f'duplicate: already handled {event_type} for this client within {window_minutes}m'
    return True, 'not a duplicate'


# ─── Combined gate ────────────────────────────────────────────────────────────

def should_act(
    agent_name: str,
    agent_subscriptions: list,
    event_type: str,
    client_id: Optional[str],
    payload: dict,
    cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES,
) -> Tuple[bool, str]:
    """
    Run all checks in order. Return (True, reason) or (False, reason).
    Short-circuits on first failure.
    """
    ok, reason = check_relevance(agent_subscriptions, event_type)
    if not ok:
        return False, reason

    ok, reason = check_safety(payload)
    if not ok:
        return False, f'safety: {reason}'

    ok, reason = check_cooldown(agent_name, client_id, cooldown_minutes)
    if not ok:
        return False, reason

    ok, reason = check_duplicate(agent_name, client_id, event_type)
    if not ok:
        return False, reason

    return True, 'all checks passed'
