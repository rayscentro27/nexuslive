"""
Funnel Registry.

CRUD for the `funnels` and `funnel_steps` tables.

These are marketing/deployment funnels attached to nexus instances —
distinct from funnel_service.py which tracks client lifecycle stages.

Funnel types: lead_gen, sales, onboarding, upsell
Step types:   message, form, offer, redirect, delay

Usage:
    from funnel_engine.funnel_registry import (
        create_funnel, add_step, get_funnel, list_funnel_steps,
        activate_funnel, pause_funnel,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('FunnelRegistry')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

VALID_FUNNEL_TYPES = {'lead_gen', 'sales', 'onboarding', 'upsell'}
VALID_STEP_TYPES   = {'message', 'form', 'offer', 'redirect', 'delay'}
VALID_STATUSES     = {'draft', 'active', 'paused', 'archived'}


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


# ─── Funnels ──────────────────────────────────────────────────────────────────

def create_funnel(
    funnel_name: str,
    funnel_type: str            = 'lead_gen',
    instance_id: Optional[str] = None,
    niche: Optional[str]       = None,
    config: Optional[dict]     = None,
) -> Optional[dict]:
    """Create a new funnel (status=draft)."""
    row: dict = {
        'funnel_name': funnel_name,
        'funnel_type': funnel_type if funnel_type in VALID_FUNNEL_TYPES else 'lead_gen',
        'status':      'draft',
        'config':      config or {},
    }
    if instance_id:
        row['instance_id'] = instance_id
    if niche:
        row['niche'] = niche
    return _sb_post('funnels', row)


def get_funnel(funnel_id: str) -> Optional[dict]:
    rows = _sb_get(f"funnels?id=eq.{funnel_id}&select=*&limit=1")
    return rows[0] if rows else None


def list_funnels(
    instance_id: Optional[str] = None,
    status: Optional[str]      = None,
    niche: Optional[str]       = None,
    limit: int                 = 50,
) -> List[dict]:
    parts = [f"select=*&order=created_at.desc&limit={limit}"]
    if instance_id:
        parts.append(f"instance_id=eq.{instance_id}")
    if status:
        parts.append(f"status=eq.{status}")
    if niche:
        parts.append(f"niche=eq.{niche}")
    return _sb_get(f"funnels?{'&'.join(parts)}")


def activate_funnel(funnel_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"funnels?id=eq.{funnel_id}",
        {'status': 'active', 'updated_at': now},
    )


def pause_funnel(funnel_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"funnels?id=eq.{funnel_id}",
        {'status': 'paused', 'updated_at': now},
    )


def archive_funnel(funnel_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"funnels?id=eq.{funnel_id}",
        {'status': 'archived', 'updated_at': now},
    )


# ─── Funnel Steps ─────────────────────────────────────────────────────────────

def add_step(
    funnel_id: str,
    step_name: str,
    step_order: int,
    step_type: str          = 'message',
    content: Optional[str] = None,
    config: Optional[dict] = None,
) -> Optional[dict]:
    """Add a step to a funnel. UNIQUE(funnel_id, step_order)."""
    row: dict = {
        'funnel_id':  funnel_id,
        'step_name':  step_name,
        'step_order': step_order,
        'step_type':  step_type if step_type in VALID_STEP_TYPES else 'message',
        'config':     config or {},
    }
    if content:
        row['content'] = content
    return _sb_post('funnel_steps', row)


def list_funnel_steps(funnel_id: str) -> List[dict]:
    """Return steps in order."""
    return _sb_get(
        f"funnel_steps?funnel_id=eq.{funnel_id}&select=*&order=step_order.asc"
    )


def get_step_count(funnel_id: str) -> int:
    rows = _sb_get(
        f"funnel_steps?funnel_id=eq.{funnel_id}&select=id"
    )
    return len(rows)
