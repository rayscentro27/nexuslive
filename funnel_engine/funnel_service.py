"""
Funnel Service.

Manages funnel_events and funnel_stage_tracking.

Stages (ordered):
  lead_captured → onboarding_started → credit_improved →
  funding_applied → funding_received → capital_allocated

Each client has one row in funnel_stage_tracking (their current stage).
funnel_events is an append-only log of every stage transition.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('FunnelService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

FUNNEL_STAGES = [
    'lead_captured',
    'onboarding_started',
    'credit_improved',
    'funding_applied',
    'funding_received',
    'capital_allocated',
]


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


# ─── Funnel Events ────────────────────────────────────────────────────────────

def record_funnel_event(
    stage: str,
    client_id: Optional[str] = None,
    lead_id: Optional[str]   = None,
    event_source: str        = 'system',
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """Append a funnel event. Returns event id."""
    row: dict = {
        'stage':        stage,
        'event_source': event_source,
        'metadata':     metadata or {},
    }
    if client_id:
        row['client_id'] = client_id
    if lead_id:
        row['lead_id'] = lead_id
    result = _sb_post('funnel_events', row)
    if result:
        logger.info(f"Funnel event: {stage} client={client_id or lead_id}")
    return result.get('id') if result else None


# ─── Stage Tracking ───────────────────────────────────────────────────────────

def get_funnel_stage(client_id: str) -> Optional[dict]:
    rows = _sb_get(
        f"funnel_stage_tracking?client_id=eq.{client_id}&select=*&limit=1"
    )
    return rows[0] if rows else None


def update_funnel_stage(client_id: str, new_stage: str) -> bool:
    """
    Upsert the stage tracking row.
    Advances stage only if new_stage is further along in FUNNEL_STAGES.
    """
    if new_stage not in FUNNEL_STAGES:
        logger.warning(f"Unknown funnel stage: {new_stage}")
        return False

    now      = datetime.now(timezone.utc).isoformat()
    existing = get_funnel_stage(client_id)

    if existing:
        current = existing.get('current_stage', 'lead_captured')
        current_idx = FUNNEL_STAGES.index(current) if current in FUNNEL_STAGES else 0
        new_idx     = FUNNEL_STAGES.index(new_stage)
        if new_idx <= current_idx:
            # Don't go backwards
            return True

        ok = _sb_patch(
            f"funnel_stage_tracking?client_id=eq.{client_id}",
            {
                'current_stage':    new_stage,
                'previous_stage':   current,
                'days_in_stage':    0,
                'stage_entered_at': now,
                'last_activity_at': now,
            },
        )
    else:
        # Create new row
        url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/funnel_stage_tracking"
        body = json.dumps({
            'client_id':        client_id,
            'current_stage':    new_stage,
            'stage_entered_at': now,
            'last_activity_at': now,
        }).encode()
        h = _headers()
        h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        req = urllib.request.Request(url, data=body, headers=h, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as _:
                ok = True
        except Exception as e:
            logger.error(f"Upsert funnel stage → {e}")
            ok = False

    if ok:
        logger.info(f"Funnel stage: client={client_id} → {new_stage}")
    return ok


def get_stage_report() -> dict:
    """Return count of clients per funnel stage."""
    rows = _sb_get("funnel_stage_tracking?select=current_stage&limit=2000")
    counts: dict = {}
    for r in rows:
        stage = r.get('current_stage', 'unknown')
        counts[stage] = counts.get(stage, 0) + 1
    return {stage: counts.get(stage, 0) for stage in FUNNEL_STAGES}


def get_clients_at_stage(stage: str, limit: int = 100) -> List[dict]:
    return _sb_get(
        f"funnel_stage_tracking?current_stage=eq.{stage}"
        f"&order=stage_entered_at.asc&limit={limit}&select=*"
    )


def get_stalled_clients(days: int = 14, limit: int = 50) -> List[dict]:
    """Return clients who haven't progressed in N days."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return _sb_get(
        f"funnel_stage_tracking?last_activity_at=lt.{cutoff}"
        f"&order=last_activity_at.asc&limit={limit}&select=*"
    )
