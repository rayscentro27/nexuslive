"""
Command Approval Service.

Creates and manages command_approvals records.
The executor reads approval status before running any command.

Approval flow by safety level:
  low    → approval_status = 'not_required'  → executes immediately
  medium → approval_status = 'pending'       → waits for explicit approval
  high   → approval_status = 'pending'       → waits for explicit approval

To approve from Telegram or API:
    approve_command(command_id, approved_by='ray', notes='Verified OK')

Risk tiers:
  LOW    — add_research_source, rescan_source
  MEDIUM — rerun_funding_analysis, rerun_credit_analysis, refresh_strategy_scores
  HIGH   — pause_pipeline, resume_pipeline, disable_source
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('ApprovalService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Maps command_type → approval_level
COMMAND_RISK_MAP = {
    'add_research_source':    'low',
    'rescan_source':          'low',
    'rerun_funding_analysis': 'medium',
    'rerun_credit_analysis':  'medium',
    'refresh_strategy_scores': 'medium',
    'pause_pipeline':         'high',
    'resume_pipeline':        'high',
    'disable_source':         'high',
}

# Default if command_type not in map
_DEFAULT_LEVEL = 'medium'


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
            return None  # already exists
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


# ─── Public API ───────────────────────────────────────────────────────────────

def create_approval_record(
    command_id: str,
    command_type: Optional[str] = None,
    safety_level: Optional[str] = None,
) -> Optional[str]:
    """
    Create a command_approvals row for a new command.
    Returns the approval row id, or None on failure.
    """
    level  = safety_level or COMMAND_RISK_MAP.get(command_type or '', _DEFAULT_LEVEL)
    status = 'not_required' if level == 'low' else 'pending'

    row = {
        'command_id':      command_id,
        'approval_level':  level,
        'approval_status': status,
    }
    result = _sb_post('command_approvals', row)
    if result:
        logger.debug(f"Approval record created: cmd={command_id} level={level} status={status}")
        return result.get('id')
    return None


def get_approval(command_id: str) -> Optional[dict]:
    """Return the approval record for a command_id."""
    rows = _sb_get(
        f"command_approvals?command_id=eq.{command_id}&select=*&limit=1"
    )
    return rows[0] if rows else None


def is_approved(command_id: str) -> bool:
    """
    Return True if this command can proceed.
    True when: approval_status = 'not_required' OR 'approved'
    """
    rec = get_approval(command_id)
    if not rec:
        return False
    return rec.get('approval_status') in ('not_required', 'approved')


def approve_command(
    command_id: str,
    approved_by: str     = 'admin',
    notes: Optional[str] = None,
) -> bool:
    """Grant approval for a pending command."""
    now  = datetime.now(timezone.utc).isoformat()
    body: dict = {
        'approval_status': 'approved',
        'approved_by':     approved_by,
        'approved_at':     now,
    }
    if notes:
        body['notes'] = notes
    ok = _sb_patch(f"command_approvals?command_id=eq.{command_id}", body)
    if ok:
        logger.info(f"Command approved: cmd={command_id} by={approved_by}")
    return ok


def reject_command(
    command_id: str,
    rejected_by: str     = 'admin',
    notes: Optional[str] = None,
) -> bool:
    """Reject a pending command (stores who rejected and why)."""
    now  = datetime.now(timezone.utc).isoformat()
    body: dict = {
        'approval_status': 'rejected',
        'approved_by':     rejected_by,
        'approved_at':     now,
    }
    if notes:
        body['notes'] = notes
    ok = _sb_patch(f"command_approvals?command_id=eq.{command_id}", body)
    if ok:
        logger.info(f"Command rejected: cmd={command_id} by={rejected_by}")
    return ok


def get_pending_approvals(limit: int = 50) -> List[dict]:
    """Return all commands awaiting approval — for the admin UI."""
    rows = _sb_get(
        f"command_approvals?approval_status=eq.pending&order=created_at.asc&limit={limit}&select=*"
    )
    return rows


def get_recent_approvals(hours: int = 48, limit: int = 100) -> List[dict]:
    """Return recent approval activity (audit log)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return _sb_get(
        f"command_approvals?created_at=gt.{cutoff}&order=created_at.desc&limit={limit}&select=*"
    )
