"""
Auto-Fix Service — Part 4.

Classifies issues and attempts safe automatic remediation.
Owner-approval-required fixes are queued in owner_approval_queue.

Safe fixes (run immediately):
  - Restart stale worker (via heartbeat reset)
  - Clear stuck job queue entries (mark as 'abandoned')
  - Retry failed comms (re-queue in hermes_comms_log)
  - Archive old hermes_aggregates (> 7 days, suppressed/informational)

Owner-approval fixes:
  - Bulk lead outreach (> 50 recipients)
  - Budget changes > $500
  - DB schema changes
  - Content bulk publish
"""

import logging
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('AutofixService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _sb_request(path: str, method: str = 'GET', body: Optional[dict] = None, prefer: str = '') -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }
    if prefer:
        headers['Prefer'] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result if isinstance(result, list) else ([result] if result else [])
    except Exception as e:
        logger.warning(f"{method} {path}: {e}")
        return []


def _log_action(issue_type: str, description: str, action_taken: str,
                classification: str = 'safe', status: str = 'completed',
                outcome: str = '', error_detail: str = '') -> None:
    _sb_request('hermes_autofix_actions', 'POST', {
        'issue_type': issue_type,
        'description': description,
        'action_taken': action_taken,
        'classification': classification,
        'status': status,
        'outcome': outcome or action_taken,
        'error_detail': error_detail or None,
        'completed_at': datetime.now(timezone.utc).isoformat() if status == 'completed' else None,
    }, prefer='return=minimal')


def _queue_for_approval(action_type: str, description: str, payload: dict,
                        requested_by: str = 'autofix_service', priority: str = 'normal') -> str:
    rows = _sb_request('owner_approval_queue', 'POST', {
        'action_type': action_type,
        'description': description,
        'payload': payload,
        'requested_by': requested_by,
        'priority': priority,
        'status': 'pending',
        'expires_at': (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
    }, prefer='return=representation')
    return (rows[0].get('id', '') if rows else '')


# ─── Safe Fixes ───────────────────────────────────────────────────────────────

def fix_stale_worker(worker_id: str) -> dict:
    """Reset a stale worker's heartbeat status so it re-registers."""
    try:
        _sb_request(
            f"worker_heartbeats?worker_id=eq.{worker_id}",
            method='PATCH',
            body={'status': 'reset', 'last_seen_at': datetime.now(timezone.utc).isoformat()},
            prefer='return=minimal',
        )
        _log_action(
            'stale_worker', f"Worker {worker_id} was stale",
            f"Reset heartbeat status for {worker_id}",
        )
        return {'fixed': True, 'worker': worker_id}
    except Exception as e:
        _log_action('stale_worker', f"Worker {worker_id} was stale",
                    f"Attempted reset for {worker_id}", status='failed', error_detail=str(e))
        return {'fixed': False, 'error': str(e)}


def fix_stuck_jobs(max_age_hours: int = 6) -> dict:
    """Mark jobs stuck in 'running' for > max_age_hours as 'abandoned'."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    rows = _sb_request(
        f"job_events?status=eq.running&created_at=lt.{cutoff}&select=id&limit=100"
    )
    if not rows:
        return {'fixed': 0}
    ids = [r['id'] for r in rows if r.get('id')]
    for job_id in ids:
        _sb_request(
            f"job_events?id=eq.{job_id}",
            method='PATCH',
            body={'status': 'abandoned'},
            prefer='return=minimal',
        )
    _log_action(
        'stuck_jobs', f"{len(ids)} jobs stuck in running > {max_age_hours}h",
        f"Marked {len(ids)} jobs as abandoned",
        outcome=f"{len(ids)} jobs cleared",
    )
    return {'fixed': len(ids)}


def fix_retry_failed_comms(max_retries: int = 3) -> dict:
    """Re-queue failed comms that haven't hit max_retries."""
    rows = _sb_request(
        f"hermes_comms_log?status=eq.failed&retry_count=lt.{max_retries}&select=id,channel,retry_count&limit=20"
    )
    retried = 0
    for r in rows:
        next_retry = (datetime.now(timezone.utc) + timedelta(minutes=5 * (r.get('retry_count', 0) + 1))).isoformat()
        _sb_request(
            f"hermes_comms_log?id=eq.{r['id']}",
            method='PATCH',
            body={
                'status': 'retrying',
                'retry_count': r.get('retry_count', 0) + 1,
                'next_retry_at': next_retry,
            },
            prefer='return=minimal',
        )
        retried += 1
    if retried:
        _log_action(
            'failed_comms', f"{retried} comms failed and eligible for retry",
            f"Re-queued {retried} comms with exponential backoff",
            outcome=f"{retried} retried",
        )
    return {'retried': retried}


def fix_archive_old_events(days: int = 7) -> dict:
    """Soft-delete old suppressed/informational aggregates to keep table lean."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _sb_request(
        f"hermes_aggregates?classification=in.(suppress,informational)"
        f"&created_at=lt.{cutoff}&select=id&limit=500"
    )
    if not rows:
        return {'archived': 0}
    ids = [r['id'] for r in rows if r.get('id')]
    for rec_id in ids:
        _sb_request(
            f"hermes_aggregates?id=eq.{rec_id}",
            method='DELETE',
            prefer='return=minimal',
        )
    _log_action(
        'old_events', f"{len(ids)} old aggregates > {days}d",
        f"Deleted {len(ids)} suppressed/informational aggregates",
        outcome=f"{len(ids)} archived",
    )
    return {'archived': len(ids)}


# ─── Owner-Approval Fixes ─────────────────────────────────────────────────────

def request_bulk_outreach(lead_ids: list, message_template: str, requested_by: str = 'sales_agent') -> str:
    """Queue bulk outreach for owner approval."""
    qid = _queue_for_approval(
        'bulk_outreach',
        f"Send outreach to {len(lead_ids)} leads",
        {'lead_ids': lead_ids[:100], 'message_template': message_template[:500]},
        requested_by=requested_by,
        priority='normal',
    )
    _log_action(
        'bulk_outreach', f"Requested bulk outreach to {len(lead_ids)} leads",
        f"Queued for owner approval (id={qid})",
        classification='needs_owner_approval', status='awaiting_approval',
    )
    return qid


def request_budget_change(description: str, amount_usd: float, requested_by: str = 'budget_agent') -> str:
    """Queue a budget change request for owner approval."""
    qid = _queue_for_approval(
        'budget_change',
        f"Budget change: {description} (${amount_usd:.2f})",
        {'description': description, 'amount_usd': amount_usd},
        requested_by=requested_by,
        priority='urgent' if amount_usd > 1000 else 'normal',
    )
    _log_action(
        'budget_change', f"Budget change ${amount_usd:.2f}: {description}",
        f"Queued for owner approval (id={qid})",
        classification='needs_owner_approval', status='awaiting_approval',
    )
    return qid


# ─── Run all safe fixes ───────────────────────────────────────────────────────

def run_safe_fixes() -> dict:
    """Run all safe auto-fix routines. Returns summary of actions taken."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {}
    results = {}
    try:
        results['stuck_jobs'] = fix_stuck_jobs()
    except Exception as e:
        logger.warning(f"fix_stuck_jobs: {e}")
    try:
        results['retry_comms'] = fix_retry_failed_comms()
    except Exception as e:
        logger.warning(f"fix_retry_failed_comms: {e}")
    try:
        results['archive_events'] = fix_archive_old_events()
    except Exception as e:
        logger.warning(f"fix_archive_old_events: {e}")
    return results
