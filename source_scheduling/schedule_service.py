"""
Schedule Service.

CRUD helpers for source_schedules.
Used by the scheduler_worker (polling) and policy_service (auto-create).

Schedule types:
  manual   — no automatic runs; only triggers on admin command
  interval — runs every N minutes
  daily    — runs once per day (treated as interval=1440)
  weekly   — runs once per week (interval=10080)
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('ScheduleService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

_INTERVAL_MAP = {
    'daily':  1440,
    'weekly': 10080,
}


def _headers() -> dict:
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
        if e.code == 409:
            return None  # duplicate source_id, handled by caller
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


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_interval(schedule_type: str, interval_minutes: Optional[int]) -> int:
    """Return interval in minutes for any schedule type."""
    if schedule_type == 'manual':
        return 0
    if schedule_type == 'interval':
        return interval_minutes or 1440
    return _INTERVAL_MAP.get(schedule_type, 1440)


def _next_run(schedule_type: str, interval_minutes: Optional[int],
              from_time: Optional[datetime] = None) -> Optional[str]:
    """Compute next_run_at from now (or from_time) based on schedule_type."""
    if schedule_type == 'manual':
        return None
    base     = from_time or datetime.now(timezone.utc)
    interval = _resolve_interval(schedule_type, interval_minutes)
    return (base + timedelta(minutes=interval)).isoformat()


# ─── Public API ───────────────────────────────────────────────────────────────

def create_schedule(
    source_id: str,
    schedule_type: str       = 'daily',
    interval_minutes: Optional[int] = None,
    start_immediately: bool  = False,
) -> Optional[str]:
    """
    Create a new schedule for a source.
    Returns the schedule row id, or None on failure/duplicate.
    """
    now = datetime.now(timezone.utc)
    if start_immediately or schedule_type != 'manual':
        first_run = now.isoformat()          # run ASAP on first pick-up
    else:
        first_run = None

    row: dict = {
        'source_id':      source_id,
        'schedule_type':  schedule_type,
        'status':         'active',
        'updated_at':     now.isoformat(),
    }
    if interval_minutes is not None:
        row['interval_minutes'] = interval_minutes
    elif schedule_type in _INTERVAL_MAP:
        row['interval_minutes'] = _INTERVAL_MAP[schedule_type]
    if first_run:
        row['next_run_at'] = first_run

    result = _sb_post('source_schedules', row)
    if result:
        logger.info(f"Schedule created: source={source_id} type={schedule_type}")
        return result.get('id')
    return None


def get_due_schedules(limit: int = 50) -> List[dict]:
    """Return active schedules whose next_run_at is in the past."""
    now = datetime.now(timezone.utc).isoformat()
    return _sb_get(
        f"source_schedules"
        f"?status=eq.active"
        f"&next_run_at=lte.{now}"
        f"&schedule_type=neq.manual"
        f"&select=*&order=next_run_at.asc&limit={limit}"
    )


def advance_schedule(schedule_id: str, schedule_type: str,
                     interval_minutes: Optional[int] = None) -> bool:
    """
    After a run: set last_run_at=now, compute and set next_run_at.
    """
    now      = datetime.now(timezone.utc)
    next_run = _next_run(schedule_type, interval_minutes, from_time=now)
    body: dict = {
        'last_run_at': now.isoformat(),
        'updated_at':  now.isoformat(),
    }
    if next_run:
        body['next_run_at'] = next_run
    return _sb_patch(f"source_schedules?id=eq.{schedule_id}", body)


def get_schedule_for_source(source_id: str) -> Optional[dict]:
    rows = _sb_get(
        f"source_schedules?source_id=eq.{source_id}&select=*&limit=1"
    )
    return rows[0] if rows else None


def pause_source_schedule(source_id: str) -> bool:
    """Pause scheduling for a source (keep next_run_at but won't fire)."""
    return _sb_patch(
        f"source_schedules?source_id=eq.{source_id}",
        {'status': 'paused', 'updated_at': datetime.now(timezone.utc).isoformat()},
    )


def resume_source_schedule(source_id: str) -> bool:
    """Resume a paused schedule, setting next_run_at=now so it fires soon."""
    now = datetime.now(timezone.utc)
    return _sb_patch(
        f"source_schedules?source_id=eq.{source_id}",
        {
            'status':      'active',
            'next_run_at': now.isoformat(),
            'updated_at':  now.isoformat(),
        },
    )


def disable_source_schedule(source_id: str) -> bool:
    """Permanently disable scheduling (requires manual re-enable)."""
    return _sb_patch(
        f"source_schedules?source_id=eq.{source_id}",
        {'status': 'disabled', 'updated_at': datetime.now(timezone.utc).isoformat()},
    )


def get_all_schedules(status: Optional[str] = None, limit: int = 200) -> List[dict]:
    """Return schedules, optionally filtered by status."""
    parts = [f'limit={limit}', 'select=*', 'order=next_run_at.asc']
    if status:
        parts.append(f'status=eq.{status}')
    return _sb_get(f"source_schedules?{'&'.join(parts)}")
