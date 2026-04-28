"""
Nexus One Reporting Layer.

Aggregates real system state from all data sources into executive views.
All reads are from Supabase — no fabrication.

Supported output queries:
  - daily_brief()           — full system state for daily briefing
  - attention_required()    — what needs the operator now
  - what_changed()          — delta since last briefing
  - critical_alerts()       — urgent blockers only
  - pending_reviews()       — all items awaiting human decision

Usage:
    from nexus_one.reporting_layer import (
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14
        daily_brief, attention_required, critical_alerts, pending_reviews,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('NexusOneReporting')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _sb_get(path: str, default: list = None) -> list:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.debug(f"GET {path} → {e}")
        return default or []


# ─── Component readers ─────────────────────────────────────────────────────────

def _read_worker_health() -> dict:
    """Check recent agent summaries for failures/skips."""
    rows = _sb_get(
        "agent_run_summaries?select=agent_name,status,created_at"
        "&order=created_at.desc&limit=50"
    )
    failures = [r for r in rows if r.get('status') in ('failed', 'error')]
    skipped  = [r for r in rows if r.get('status') == 'skipped']
    return {
        'total_recent':   len(rows),
        'failures':       failures[:5],
        'failure_count':  len(failures),
        'skipped_count':  len(skipped),
    }


def _read_pending_decisions() -> dict:
    """Kill/scale decisions awaiting approval."""
    decisions = _sb_get(
        "instance_decisions?status=eq.pending&select=id,decision,reason,created_at"
        "&order=created_at.desc&limit=20"
    )
    scale = [d for d in decisions if d.get('decision') == 'scale']
    kill  = [d for d in decisions if d.get('decision') == 'kill']
    hold  = [d for d in decisions if d.get('decision') == 'hold']
    return {
        'total':   len(decisions),
        'scale':   len(scale),
        'kill':    len(kill),
        'hold':    len(hold),
        'records': decisions[:5],
    }


def _read_pending_variants() -> List[dict]:
    """Improvement variants awaiting human approval."""
    return _sb_get(
        "candidate_variants?status=eq.scored&select=id,variant_name,sim_score,experiment_id"
        "&order=sim_score.desc&limit=10"
    )


def _read_pending_commands() -> List[dict]:
    """Admin commands awaiting approval."""
    return _sb_get(
        "admin_commands?status=eq.pending_approval&select=id,command_type,raw_command,risk_level"
        "&order=created_at.desc&limit=10"
    )


def _read_source_health() -> dict:
    """Source health overview."""
    all_scores = _sb_get(
        "source_health_scores?select=total_score,freshness_score&order=total_score.asc&limit=100"
    )
    if not all_scores:
        return {'count': 0, 'avg_score': 0, 'critical_count': 0}
    scores     = [float(r.get('total_score', 0)) for r in all_scores]
    avg_score  = round(sum(scores) / len(scores), 1)
    critical   = [s for s in scores if s < 30]
    return {
        'count':          len(scores),
        'avg_score':      avg_score,
        'critical_count': len(critical),
    }


def _read_portfolio_state() -> dict:
    """Latest portfolio snapshot."""
    rows = _sb_get(
        "portfolio_summary?select=monthly_revenue,active_instances,testing_instances,"
        "killed_instances,top_performers,underperformers&order=snapshot_at.desc&limit=1"
    )
    return rows[0] if rows else {}


def _read_revenue_today() -> float:
    """Monthly revenue total for current period."""
    period = datetime.now(timezone.utc).strftime('%Y-%m')
    rows   = _sb_get(f"revenue_streams?period=eq.{period}&select=revenue")
    return round(sum(float(r.get('revenue', 0)) for r in rows), 2)


def _read_latest_briefing_time() -> Optional[str]:
    """When was the last CEO briefing generated."""
    rows = _sb_get(
        "executive_briefings?select=created_at&order=created_at.desc&limit=1"
    )
    return rows[0].get('created_at') if rows else None


def _read_critical_blockers() -> List[str]:
    """Read coordination blockers and critical alerts."""
    blockers = []

    # Check for critical worker failures
    health = _read_worker_health()
    if health['failure_count'] >= 3:
        blockers.append(f"{health['failure_count']} agent failures in recent runs")

    # Check source health
    source = _read_source_health()
    if source.get('critical_count', 0) >= 5:
        blockers.append(f"{source['critical_count']} sources critically low health (<30)")

    # Check portfolio for kill decisions
    decisions = _read_pending_decisions()
    if decisions.get('kill', 0) > 0:
        blockers.append(f"{decisions['kill']} instances flagged for kill — awaiting your approval")

    return blockers


# ─── Executive output builders ─────────────────────────────────────────────────

def daily_brief() -> dict:
    """
    Full daily executive brief.
    Aggregates all system signals into one structured object.
    """
    portfolio    = _read_portfolio_state()
    revenue      = _read_revenue_today()
    decisions    = _read_pending_decisions()
    variants     = _read_pending_variants()
    commands     = _read_pending_commands()
    worker_hlt   = _read_worker_health()
    source_hlt   = _read_source_health()
    blockers     = _read_critical_blockers()
    last_brief   = _read_latest_briefing_time()

    from nexus_one.identity import classify_urgency
    urgency = classify_urgency(
        has_critical_alert=len(blockers) > 0,
        pending_approvals=decisions['total'] + len(variants) + len(commands),
        worker_failures=worker_hlt['failure_count'],
        revenue_zero=revenue == 0,
        kill_decisions=decisions.get('kill', 0),
    )

    return {
        'generated_at':    datetime.now(timezone.utc).isoformat(),
        'urgency':         urgency,
        'revenue_month':   revenue,
        'portfolio':       portfolio,
        'pending': {
            'decisions':   decisions,
            'variants':    variants,
            'commands':    commands,
        },
        'worker_health':   worker_hlt,
        'source_health':   source_hlt,
        'blockers':        blockers,
        'last_brief_at':   last_brief,
    }


def attention_required() -> dict:
    """Only the items needing operator action right now."""
    decisions = _read_pending_decisions()
    variants  = _read_pending_variants()
    commands  = _read_pending_commands()
    blockers  = _read_critical_blockers()

    items = []

    if blockers:
        for b in blockers:
            items.append({'urgency': 'high', 'type': 'blocker', 'text': b})

    for d in decisions.get('records', []):
        if d.get('decision') == 'kill':
            items.append({'urgency': 'high', 'type': 'kill_decision', 'id': d['id'], 'text': d.get('reason', '')[:80]})
        elif d.get('decision') == 'scale':
            items.append({'urgency': 'medium', 'type': 'scale_decision', 'id': d['id'], 'text': d.get('reason', '')[:80]})

    for v in variants[:3]:
        items.append({'urgency': 'medium', 'type': 'variant_review', 'id': v['id'],
                      'text': f"{v.get('variant_name','')} — sim_score={v.get('sim_score','?')}"})

    for c in commands[:3]:
        items.append({'urgency': 'medium' if c.get('risk_level') == 'medium' else 'high',
                      'type': 'command_approval', 'id': c['id'],
                      'text': c.get('raw_command', '')[:80]})

    # Sort by urgency
    urgency_order = {'high': 0, 'critical': 0, 'medium': 1, 'low': 2}
    items.sort(key=lambda x: urgency_order.get(x.get('urgency', 'low'), 3))

    return {
        'total_items': len(items),
        'items':       items,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }


def what_changed(hours: int = 24) -> dict:
    """Delta report: what happened since N hours ago."""
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    new_decisions = _sb_get(
        f"instance_decisions?created_at=gt.{since}&select=decision,reason&limit=20"
    )
    new_summaries = _sb_get(
        f"agent_run_summaries?created_at=gt.{since}&select=agent_name,status&limit=50"
    )
    new_variants  = _sb_get(
        f"candidate_variants?created_at=gt.{since}&select=variant_name,status&limit=10"
    )
    new_commands  = _sb_get(
        f"admin_commands?created_at=gt.{since}&select=command_type,status&limit=10"
    )

    completed_agents = [s for s in new_summaries if s.get('status') == 'completed']
    failed_agents    = [s for s in new_summaries if s.get('status') in ('failed', 'error')]

    return {
        'since_hours':       hours,
        'since':             since,
        'new_decisions':     new_decisions,
        'agent_runs':        len(new_summaries),
        'completed_agents':  len(completed_agents),
        'failed_agents':     len(failed_agents),
        'new_variants':      new_variants,
        'new_commands':      new_commands,
    }


def critical_alerts() -> List[dict]:
    """Critical-only alerts. Empty list = all clear."""
    blockers = _read_critical_blockers()
    alerts   = []
    for b in blockers:
        alerts.append({
            'issue':     b,
            'urgency':   'high',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    return alerts


def pending_reviews() -> dict:
    """All items awaiting human review/approval."""
    return {
        'decisions':   _read_pending_decisions(),
        'variants':    _read_pending_variants(),
        'commands':    _read_pending_commands(),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }
