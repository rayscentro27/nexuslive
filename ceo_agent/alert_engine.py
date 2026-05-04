"""
CEO Alert Engine — Part 2.

Evaluates 12 critical alert conditions against live Supabase data.
Deduplicates via cooldown tracked in hermes_aggregates.
Each fired alert is logged and returned as a structured dict.

Alert format:
  {
    'type': str,         # ALERT_TYPE constant
    'severity': str,     # critical | high | medium
    'summary': str,
    'action': str,
    'data': dict,
  }
"""

import logging
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

logger = logging.getLogger('AlertEngine')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Configurable thresholds
CLIENT_STUCK_HOURS      = int(os.getenv('ALERT_CLIENT_STUCK_HOURS',      '48'))
NO_REVENUE_DAYS         = int(os.getenv('ALERT_NO_REVENUE_DAYS',         '3'))
AGENT_FAILURE_THRESHOLD = int(os.getenv('ALERT_AGENT_FAILURE_THRESHOLD', '2'))
GRANT_DEADLINE_DAYS     = int(os.getenv('ALERT_GRANT_DEADLINE_DAYS',     '7'))
APPROVAL_QUEUE_HOURS    = int(os.getenv('ALERT_APPROVAL_QUEUE_HOURS',    '24'))
ERROR_RATE_PCT          = float(os.getenv('ALERT_ERROR_RATE_PCT',        '5.0'))
COST_DAILY_USD          = float(os.getenv('ALERT_COST_DAILY_USD',        '10.0'))
LEAD_NOFOLLOWUP_HOURS   = int(os.getenv('ALERT_LEAD_NOFOLLOWUP_HOURS',  '24'))
COMMS_FAILURE_COUNT     = int(os.getenv('ALERT_COMMS_FAILURE_COUNT',     '3'))
ALERT_COOLDOWN_HOURS    = int(os.getenv('ALERT_COOLDOWN_HOURS',          '4'))


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result if isinstance(result, list) else []
    except Exception as e:
        logger.debug(f"_sb_get {path}: {e}")
        return []


def _sb_post(path: str, body: dict, prefer: str = '') -> None:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }
    if prefer:
        headers['Prefer'] = prefer
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            pass
    except Exception as e:
        logger.warning(f"_sb_post {path}: {e}")


def _cooldown_active(alert_type: str) -> bool:
    """Return True if this alert type fired recently and is still cooling down."""
    if not SUPABASE_URL:
        return False
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)).isoformat()
    rows = _sb_get(
        f"hermes_aggregates?event_type=eq.{alert_type}"
        f"&alert_sent=eq.true"
        f"&created_at=gt.{cutoff}"
        f"&limit=1"
    )
    return len(rows) > 0


def _log_alert(alert_type: str, summary: str, classification: str = 'critical_alert') -> None:
    _sb_post('hermes_aggregates', {
        'event_source': 'alert_engine',
        'event_type': alert_type,
        'classification': classification,
        'aggregated_summary': summary,
        'alert_sent': True,
    }, prefer='return=minimal')


def _build_alert(type_: str, severity: str, summary: str, action: str, data: dict) -> dict:
    return {'type': type_, 'severity': severity, 'summary': summary, 'action': action, 'data': data}


# ─── 12 Alert Checks ──────────────────────────────────────────────────────────

def check_clients_stuck() -> list:
    """Clients with readiness_score not updated in > CLIENT_STUCK_HOURS."""
    alerts = []
    if _cooldown_active('client_stuck'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=CLIENT_STUCK_HOURS)).isoformat()
    rows = _sb_get(
        f"user_profiles?updated_at=lt.{cutoff}"
        f"&readiness_score=lt.100"
        f"&select=id,full_name,readiness_score,updated_at&limit=10"
    )
    if rows:
        names = ', '.join(r.get('full_name', 'Unknown')[:20] for r in rows[:3])
        summary = f"{len(rows)} client(s) stuck > {CLIENT_STUCK_HOURS}h: {names}"
        _log_alert('client_stuck', summary)
        alerts.append(_build_alert(
            'CLIENT_STUCK', 'high', summary,
            'Review client progress and assign action items',
            {'count': len(rows), 'clients': rows[:5]},
        ))
    return alerts


def check_no_revenue() -> list:
    alerts = []
    if _cooldown_active('no_revenue'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(days=NO_REVENUE_DAYS)).isoformat()
    rows = _sb_get(
        f"revenue_events?created_at=gt.{cutoff}&select=id&limit=1"
    )
    if not rows:
        summary = f"No revenue events recorded in the last {NO_REVENUE_DAYS} days"
        _log_alert('no_revenue', summary)
        alerts.append(_build_alert(
            'NO_REVENUE', 'critical', summary,
            'Review sales pipeline, lead followups, and subscription renewals',
            {},
        ))
    return alerts


def check_agent_failures() -> list:
    alerts = []
    if _cooldown_active('agent_failures'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = _sb_get(
        f"job_events?status=eq.failed&created_at=gt.{cutoff}&select=agent_name,status&limit=100"
    )
    if len(rows) >= AGENT_FAILURE_THRESHOLD:
        agents = list({r.get('agent_name', '?') for r in rows})[:5]
        summary = f"{len(rows)} agent failures in the last hour: {', '.join(agents)}"
        _log_alert('agent_failures', summary)
        alerts.append(_build_alert(
            'AGENT_FAILURES', 'critical', summary,
            'Check logs and restart failed agents',
            {'count': len(rows), 'agents': agents},
        ))
    return alerts


def check_grant_deadlines() -> list:
    alerts = []
    if _cooldown_active('grant_deadline'):
        return alerts
    now = datetime.now(timezone.utc)
    cutoff = (now + timedelta(days=GRANT_DEADLINE_DAYS)).date().isoformat()
    rows = _sb_get(
        f"grants_catalog?deadline=lte.{cutoff}&deadline=gte.{now.date().isoformat()}"
        f"&is_active=eq.true&select=title,deadline&limit=10"
    )
    if rows:
        titles = ', '.join(r.get('title', '?')[:30] for r in rows[:3])
        summary = f"{len(rows)} grant deadline(s) within {GRANT_DEADLINE_DAYS} days: {titles}"
        _log_alert('grant_deadline', summary, classification='actionable')
        alerts.append(_build_alert(
            'GRANT_DEADLINE', 'high', summary,
            'Ensure eligible clients have submitted grant applications',
            {'grants': rows},
        ))
    return alerts


def check_approval_queue_stale() -> list:
    alerts = []
    if _cooldown_active('approval_queue_stale'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=APPROVAL_QUEUE_HOURS)).isoformat()
    rows = _sb_get(
        f"owner_approval_queue?status=eq.pending&created_at=lt.{cutoff}&select=id,action_type,description&limit=10"
    )
    if rows:
        summary = f"{len(rows)} approval(s) waiting > {APPROVAL_QUEUE_HOURS}h: {rows[0].get('description','?')[:60]}"
        _log_alert('approval_queue_stale', summary)
        alerts.append(_build_alert(
            'APPROVAL_QUEUE_STALE', 'high', summary,
            'Review and action pending approvals: /approvals',
            {'count': len(rows), 'items': rows[:5]},
        ))
    return alerts


def check_error_rate() -> list:
    alerts = []
    if _cooldown_active('error_rate'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    all_jobs = _sb_get(f"job_events?created_at=gt.{cutoff}&select=status&limit=500")
    if not all_jobs:
        return alerts
    failed = sum(1 for r in all_jobs if r.get('status') == 'failed')
    rate = (failed / len(all_jobs)) * 100
    if rate >= ERROR_RATE_PCT:
        summary = f"Error rate {rate:.1f}% ({failed}/{len(all_jobs)} jobs last hour)"
        _log_alert('error_rate', summary)
        alerts.append(_build_alert(
            'HIGH_ERROR_RATE', 'critical', summary,
            'Investigate failing jobs and check error_log for root cause',
            {'rate_pct': round(rate, 1), 'failed': failed, 'total': len(all_jobs)},
        ))
    return alerts


def check_ai_cost() -> list:
    alerts = []
    if _cooldown_active('ai_cost'):
        return alerts
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = _sb_get(f"ai_usage_log?created_at=gt.{today.isoformat()}&select=cost_usd&limit=10000")
    total = sum(float(r.get('cost_usd') or 0) for r in rows)
    if total >= COST_DAILY_USD:
        summary = f"AI cost today: ${total:.2f} (threshold ${COST_DAILY_USD})"
        _log_alert('ai_cost', summary)
        alerts.append(_build_alert(
            'AI_COST_SPIKE', 'high', summary,
            'Review AI usage logs and throttle non-critical agents',
            {'cost_usd': round(total, 2)},
        ))
    return alerts


def check_funding_stuck() -> list:
    alerts = []
    if _cooldown_active('funding_stuck'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    rows = _sb_get(
        f"funding_applications?status=eq.pending&updated_at=lt.{cutoff}&select=id,lender_name,requested_amount&limit=10"
    )
    if rows:
        names = ', '.join(r.get('lender_name', '?')[:20] for r in rows[:3])
        summary = f"{len(rows)} funding application(s) stuck pending > 72h: {names}"
        _log_alert('funding_stuck', summary, classification='actionable')
        alerts.append(_build_alert(
            'FUNDING_STUCK', 'high', summary,
            'Follow up with lenders or update application status',
            {'count': len(rows), 'applications': rows[:5]},
        ))
    return alerts


def check_leads_no_followup() -> list:
    alerts = []
    if _cooldown_active('leads_no_followup'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=LEAD_NOFOLLOWUP_HOURS)).isoformat()
    rows = _sb_get(
        f"leads?status=in.(new,contacted,qualified)"
        f"&next_followup_at=lt.{cutoff}"
        f"&select=id,name,status,next_followup_at&limit=10"
    )
    if rows:
        names = ', '.join(r.get('name', '?')[:20] for r in rows[:3])
        summary = f"{len(rows)} lead(s) overdue for followup: {names}"
        _log_alert('leads_no_followup', summary, classification='actionable')
        alerts.append(_build_alert(
            'LEADS_NO_FOLLOWUP', 'medium', summary,
            'Contact overdue leads: /leads',
            {'count': len(rows), 'leads': rows[:5]},
        ))
    return alerts


def check_comms_failures() -> list:
    alerts = []
    if _cooldown_active('comms_failures'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = _sb_get(
        f"hermes_comms_log?status=eq.failed&created_at=gt.{cutoff}&select=id,channel&limit=20"
    )
    if len(rows) >= COMMS_FAILURE_COUNT:
        channels = list({r.get('channel', '?') for r in rows})
        summary = f"{len(rows)} comm failure(s) in the last hour on: {', '.join(channels)}"
        _log_alert('comms_failures', summary)
        alerts.append(_build_alert(
            'COMMS_FAILURES', 'high', summary,
            'Check Telegram/email credentials and retry queue',
            {'count': len(rows), 'channels': channels},
        ))
    return alerts


def check_launch_kpi() -> list:
    alerts = []
    if _cooldown_active('launch_kpi_below_target'):
        return alerts
    today = datetime.now(timezone.utc).date().isoformat()
    rows = _sb_get(
        f"launch_metrics?period=eq.daily&period_label=eq.{today}&select=metric_name,metric_value,target_value&limit=50"
    )
    below = [
        r for r in rows
        if r.get('target_value') and float(r.get('metric_value', 0)) < float(r['target_value']) * 0.7
    ]
    if below:
        names = ', '.join(r['metric_name'] for r in below[:3])
        summary = f"{len(below)} launch KPI(s) below 70% of target today: {names}"
        _log_alert('launch_kpi_below_target', summary, classification='actionable')
        alerts.append(_build_alert(
            'LAUNCH_KPI_BELOW_TARGET', 'medium', summary,
            'Review launch metrics and adjust daily tactics: /launch',
            {'metrics': below},
        ))
    return alerts


def check_db_size_spike() -> list:
    """Check for unusually large hermes_aggregates table (proxy for data spike)."""
    alerts = []
    if _cooldown_active('db_size_spike'):
        return alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = _sb_get(
        f"hermes_aggregates?created_at=gt.{cutoff}&select=id&limit=1001"
    )
    if len(rows) > 1000:
        summary = f"DB data spike: >1000 hermes_aggregates rows in the last hour"
        _log_alert('db_size_spike', summary)
        alerts.append(_build_alert(
            'DB_SIZE_SPIKE', 'medium', summary,
            'Investigate event storm — check if suppress rules need updating',
            {'row_count': len(rows)},
        ))
    return alerts


# ─── Public API ───────────────────────────────────────────────────────────────

def run_all_checks() -> list:
    """Run all 12 alert checks. Returns list of fired alert dicts."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase not configured — skipping alert checks")
        return []

    checks = [
        check_clients_stuck,
        check_no_revenue,
        check_agent_failures,
        check_grant_deadlines,
        check_approval_queue_stale,
        check_error_rate,
        check_ai_cost,
        check_funding_stuck,
        check_leads_no_followup,
        check_comms_failures,
        check_launch_kpi,
        check_db_size_spike,
    ]

    fired = []
    for check in checks:
        try:
            fired.extend(check())
        except Exception as e:
            logger.warning(f"Alert check {check.__name__} failed: {e}")

    return fired


def format_alerts_telegram(alerts: list) -> str:
    """Format fired alerts as Telegram HTML."""
    if not alerts:
        return ''
    severity_icon = {'critical': '🚨', 'high': '⚠️', 'medium': '🔔'}
    lines = ['<b>NEXUS ALERT</b>']
    for a in alerts:
        icon = severity_icon.get(a['severity'], '•')
        lines.append(f"\n{icon} <b>[{a['type']}]</b>")
        lines.append(f"<i>{a['summary']}</i>")
        lines.append(f"→ {a['action']}")
    return '\n'.join(lines)
