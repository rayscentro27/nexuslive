"""
Heartbeat Service.

Updates the existing worker_heartbeats table so the health endpoint
can report which workers are alive vs stale.

Usage (add to the top of any worker's main loop):
    from monitoring.heartbeat_service import send_heartbeat
    send_heartbeat('signal_poller')          # at start
    send_heartbeat('signal_poller', 'idle')  # after each cycle
"""

import os
import json
import socket
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('Heartbeat')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
    }


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return []


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    h    = {**_headers(), 'Prefer': 'return=representation'}
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=h, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
            return len(rows) > 0
    except urllib.error.HTTPError as e:
        logger.debug(f"PATCH heartbeat → {e.code}")
        return False
    except Exception:
        return False


def _sb_post(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    h    = {**_headers(), 'Prefer': 'return=minimal'}
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=8) as _:
            return True
    except Exception as e:
        logger.debug(f"POST heartbeat → {e}")
        return False


def send_heartbeat(
    worker_name: str,
    status: str = 'running',
    job_type: Optional[str] = None,
    in_flight: int = 0,
    meta: Optional[dict] = None,
) -> bool:
    """
    Upsert a heartbeat row for the given worker.
    PATCH if the worker_id row exists, POST otherwise.
    Returns True on success.
    """
    now  = datetime.now(timezone.utc).isoformat()
    host = socket.gethostname()
    pid  = os.getpid()

    payload = {
        'status':             status,
        'last_heartbeat_at':  now,
        'last_seen_at':       now,
        'updated_at':         now,
        'host':               host,
        'pid':                pid,
        'in_flight_jobs':     in_flight,
        'meta':               meta or {},
    }
    if job_type:
        payload['current_job_id'] = job_type

    # Try PATCH first (worker row already exists)
    patched = _sb_patch(
        f"worker_heartbeats?worker_id=eq.{worker_name}",
        payload,
    )
    if patched:
        return True

    # First run — INSERT the row
    payload['worker_id']   = worker_name
    payload['worker_type'] = worker_name
    payload['started_at']  = now
    payload['created_at']  = now
    return _sb_post('worker_heartbeats', payload)


def mark_worker_stopped(worker_name: str) -> bool:
    """Set worker status to 'stopped' on clean shutdown."""
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"worker_heartbeats?worker_id=eq.{worker_name}",
        {'status': 'stopped', 'last_seen_at': now, 'updated_at': now},
    )
