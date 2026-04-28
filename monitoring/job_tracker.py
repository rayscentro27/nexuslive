"""
Job Tracker.

Records job lifecycle events (start → complete | fail) into job_events.
Designed to be called from any worker's main loop with minimal overhead.

Usage:
    from monitoring.job_tracker import record_job_start, record_job_complete, record_job_fail
    import time

    job_id = record_job_start('signal_poller', 'poll_cycle')
    t0 = time.time()
    try:
        # ... do work ...
        record_job_complete(job_id, int((time.time() - t0) * 1000))
    except Exception as e:
        record_job_fail(job_id, str(e), int((time.time() - t0) * 1000))
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('JobTracker')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers(prefer: str = 'return=representation') -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        prefer,
    }


def _sb_post(path: str, body: dict) -> Optional[str]:
    """Insert row, return id."""
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
            return rows[0].get('id') if rows else None
    except urllib.error.HTTPError as e:
        logger.warning(f"POST {path} → {e.code}: {e.read().decode()[:100]}")
        return None
    except Exception as e:
        logger.warning(f"POST {path} → {e}")
        return None


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


# ─── Public API ───────────────────────────────────────────────────────────────

def record_job_start(
    worker_name: str,
    job_type: Optional[str] = None,
    meta: Optional[dict]    = None,
) -> Optional[str]:
    """
    Insert a job_events row with status='started'.
    Returns the job_id (uuid) to pass to complete/fail.
    Returns None on insert failure — callers should handle gracefully.
    """
    now = datetime.now(timezone.utc).isoformat()
    row = {
        'worker_name': worker_name,
        'job_type':    job_type or worker_name,
        'status':      'started',
        'started_at':  now,
        'meta':        meta or {},
    }
    job_id = _sb_post('job_events', row)
    if job_id:
        logger.debug(f"Job started: {worker_name}/{job_type} id={job_id}")
    return job_id


def record_job_complete(
    job_id: Optional[str],
    duration_ms: int,
    meta: Optional[dict] = None,
) -> bool:
    """Mark a job as completed."""
    if not job_id:
        return False
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"job_events?id=eq.{job_id}",
        {
            'status':       'completed',
            'completed_at': now,
            'duration_ms':  duration_ms,
            'meta':         meta or {},
        },
    )


def record_job_fail(
    job_id: Optional[str],
    error_msg: str,
    duration_ms: int,
    meta: Optional[dict] = None,
) -> bool:
    """Mark a job as failed."""
    if not job_id:
        return False
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"job_events?id=eq.{job_id}",
        {
            'status':       'failed',
            'completed_at': now,
            'duration_ms':  duration_ms,
            'error_msg':    error_msg[:500],
            'meta':         meta or {},
        },
    )
