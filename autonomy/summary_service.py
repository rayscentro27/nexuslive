"""
Summary Service.

Shared utility for agents to write structured completion reports to
agent_run_summaries. Call write_summary() after any meaningful action.

Summary types:
  funding_recommendation    — agent created or declined a funding task
  funding_approved          — funding came through for a client
  credit_analysis_completed — credit score received and acted on
  credit_issues_detected    — derogatory items flagged
  capital_opportunity       — high-quality signal → capital task
  capital_deployment        — new funding → deployment plan
  client_communication      — notification task created
  milestone_notification    — client milestone communicated
  source_added              — new research source registered
  research_batch_completed  — research pipeline finished a batch
  blocker_detected          — something is stalling progress
  client_stalled            — client has had no movement past threshold

Do NOT write summaries for:
  - skipped events (decision layer block)
  - small internal coordination messages
  - failed actions (already logged in agent_action_history)
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('SummaryService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


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
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


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

def write_summary(
    agent_name: str,
    summary_type: str,
    summary_text: str,
    what_happened: str               = '',
    what_changed: str                = '',
    blockers: Optional[List[str]]    = None,
    recommended_next_action: str     = '',
    follow_up_needed: bool           = False,
    client_id: Optional[str]         = None,
    job_id: Optional[str]            = None,
    tenant_id: Optional[str]         = None,
    trigger_event_type: Optional[str] = None,
    status: str                      = 'completed',
    priority: str                    = 'medium',
    extra_payload: Optional[dict]    = None,
) -> Optional[str]:
    """
    Write a structured completion report.
    Returns the row id, or None on failure.
    Silent on error — summaries are advisory, never blocking.
    """
    structured: dict = {
        'what_happened':          what_happened or summary_text[:200],
        'what_changed':           what_changed,
        'blockers':               blockers or [],
        'recommended_next_action': recommended_next_action,
        'follow_up_needed':       follow_up_needed,
    }
    if extra_payload:
        structured.update(extra_payload)

    row: dict = {
        'agent_name':         agent_name,
        'summary_type':       summary_type,
        'summary_text':       summary_text,
        'structured_payload': structured,
        'status':             status,
        'priority':           priority,
    }
    if client_id:
        row['client_id'] = client_id
    if job_id:
        row['job_id'] = job_id
    if tenant_id:
        row['tenant_id'] = tenant_id
    if trigger_event_type:
        row['trigger_event_type'] = trigger_event_type

    try:
        result = _sb_post('agent_run_summaries', row)
        if result:
            logger.debug(f"Summary [{summary_type}] written id={result.get('id')}")
            return result.get('id')
    except Exception as e:
        logger.warning(f"write_summary failed silently: {e}")
    return None


def get_recent_summaries(
    hours: int                   = 24,
    priority: Optional[str]      = None,
    agent_name: Optional[str]    = None,
    summary_type: Optional[str]  = None,
    client_id: Optional[str]     = None,
    limit: int                   = 50,
) -> List[dict]:
    """Return recent summaries, newest first."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    parts  = [
        f'created_at=gt.{cutoff}',
        'order=created_at.desc',
        f'limit={limit}',
        'select=*',
    ]
    if priority:
        parts.append(f'priority=eq.{priority}')
    if agent_name:
        parts.append(f'agent_name=eq.{agent_name}')
    if summary_type:
        parts.append(f'summary_type=eq.{summary_type}')
    if client_id:
        parts.append(f'client_id=eq.{client_id}')
    return _sb_get(f"agent_run_summaries?{'&'.join(parts)}")


def get_summaries_for_client(client_id: str, limit: int = 10) -> List[dict]:
    """Return recent summaries for a specific client."""
    return get_recent_summaries(client_id=client_id, limit=limit)
