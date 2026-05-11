"""
Policy Service.

Reads source_scan_policies and applies them when a source is created.
Handles stale detection and priority escalation.

Policy lookup order:
  1. Match source_type + domain_keyword (most specific)
  2. Match source_type only (domain_keyword IS NULL)
  3. Fallback defaults

Domain keywords are checked via substring match against the source domain.
Example: 'grant' matches 'grants.gov', 'grantwatch.com', etc.
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('PolicyService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Fallback if no policy row exists
_DEFAULTS = {
    'default_priority':         'medium',
    'default_schedule_type':    'daily',
    'default_interval_minutes': 1440,
    'stale_after_hours':        24,
    'max_runs_per_day':         1,
}

# Domain keyword detection: keywords that appear in the source domain
_DOMAIN_KEYWORDS = [
    ('grant',   ['grant', 'usda', 'sba.gov']),
    ('funding', ['funding', 'capital', 'lender', 'loan', 'sba']),
    ('trading', ['tradingview', 'investing', 'finviz', 'bloomberg', 'nasdaq']),
]


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {'apikey': key, 'Authorization': f'Bearer {key}'}


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


# ─── Domain classification ────────────────────────────────────────────────────

def classify_domain(domain: str) -> Optional[str]:
    """
    Return a domain_keyword (e.g. 'grant', 'funding', 'trading') or None.
    Matches against known keyword groups.
    """
    lower = (domain or '').lower()
    for keyword, patterns in _DOMAIN_KEYWORDS:
        if any(p in lower for p in patterns):
            return keyword
    return None


# ─── Policy lookup ────────────────────────────────────────────────────────────

def get_policy(source_type: str, domain: Optional[str] = None) -> dict:
    """
    Return the best matching scan policy for a source type + domain.
    Falls back to _DEFAULTS if nothing found.
    """
    all_policies = _sb_get(
        f"source_scan_policies?source_type=eq.{source_type}&active=eq.true&select=*"
    )
    if not all_policies:
        return dict(_DEFAULTS)

    domain_kw = classify_domain(domain) if domain else None

    # 1. Try source_type + domain_keyword match
    if domain_kw:
        for p in all_policies:
            if p.get('domain_keyword') == domain_kw:
                return p

    # 2. Try source_type with no domain_keyword
    for p in all_policies:
        if not p.get('domain_keyword'):
            return p

    return dict(_DEFAULTS)


# ─── Policy application ───────────────────────────────────────────────────────

def apply_policy_to_source(
    source_id: str,
    source_type: str,
    domain: Optional[str] = None,
) -> dict:
    """
    Look up the matching policy and create/update a schedule for the source.
    Returns the applied policy dict.
    """
    policy = get_policy(source_type, domain)

    schedule_type    = policy.get('default_schedule_type', 'daily')
    interval_minutes = policy.get('default_interval_minutes', 1440)

    # Create schedule (silently skips if already exists)
    from source_scheduling.schedule_service import (
        create_schedule, get_schedule_for_source
    )
    existing = get_schedule_for_source(source_id)
    if not existing:
        sched_id = create_schedule(
            source_id=source_id,
            schedule_type=schedule_type,
            interval_minutes=interval_minutes,
            start_immediately=True,
        )
        if sched_id:
            logger.info(
                f"Policy applied: source={source_id} type={source_type} "
                f"schedule={schedule_type} interval={interval_minutes}m"
            )
    else:
        logger.debug(f"Schedule already exists for source={source_id}, skipping")

    return policy


# ─── Freshness + stale detection ──────────────────────────────────────────────

def get_stale_sources(limit: int = 50) -> List[dict]:
    """
    Return sources that haven't been scanned within their policy's
    stale_after_hours window.
    Joins research_sources with source_schedules.
    """
    now     = datetime.now(timezone.utc)
    results = []

    schedules = _sb_get(
        f"source_schedules?status=eq.active&select=source_id,last_run_at&limit=500"
    )
    for sched in schedules:
        source_id   = sched.get('source_id')
        last_run_at = sched.get('last_run_at')
        if not last_run_at:
            continue  # never ran — not yet stale
        # Get source details + policy
        sources = _sb_get(
            f"research_sources?id=eq.{source_id}&select=source_type,domain,label&limit=1"
        )
        if not sources:
            continue
        source = sources[0]
        policy = get_policy(source.get('source_type', 'generic'), source.get('domain'))
        stale_hours = policy.get('stale_after_hours', 24)
        last_dt     = datetime.fromisoformat(last_run_at.replace('Z', '+00:00'))
        age_hours   = (now - last_dt).total_seconds() / 3600
        if age_hours >= stale_hours:
            results.append({
                'source_id':   source_id,
                'label':       source.get('label'),
                'source_type': source.get('source_type'),
                'age_hours':   round(age_hours, 1),
                'stale_after': stale_hours,
            })
        if len(results) >= limit:
            break

    return results


def get_overdue_sources(limit: int = 50) -> List[dict]:
    """
    Return sources with next_run_at in the past that haven't been triggered.
    These are due but the scheduler may have missed them.
    """
    now = datetime.now(timezone.utc).isoformat()
    rows = _sb_get(
        f"source_schedules"
        f"?status=eq.active"
        f"&next_run_at=lte.{now}"
        f"&schedule_type=neq.manual"
        f"&select=source_id,next_run_at,schedule_type&limit={limit}"
        f"&order=next_run_at.asc"
    )
    return rows


def escalate_stale_priorities(dry_run: bool = False) -> List[str]:
    """
    For sources that are stale, bump their research_sources.priority to 'high'.
    Returns list of escalated source_ids.
    """
    import urllib.parse
    stale     = get_stale_sources(limit=20)
    escalated = []
    for s in stale:
        source_id = s['source_id']
        if not dry_run:
            url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/research_sources?id=eq.{source_id}"
            data = json.dumps({'priority': 'high'}).encode()
            h    = {
                'apikey': os.getenv('SUPABASE_KEY', SUPABASE_KEY),
                'Authorization': f'Bearer {os.getenv("SUPABASE_KEY", SUPABASE_KEY)}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal',
            }
            req  = urllib.request.Request(url, data=data, headers=h, method='PATCH')
            try:
                with urllib.request.urlopen(req, timeout=8) as _:
                    escalated.append(source_id)
            except Exception as e:
                logger.warning(f"Escalate priority failed for {source_id}: {e}")
        else:
            escalated.append(source_id)
    if escalated:
        logger.info(f"Escalated priority for {len(escalated)} stale source(s)")
    return escalated
