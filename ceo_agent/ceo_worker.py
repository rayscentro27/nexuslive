"""
CEO Worker.

Runs the CEO agent on a schedule to produce periodic executive briefings.
Also accepts on-demand runs via --type flag.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m ceo_agent.ceo_worker

Or via cron (every 6 hours):
  0 */6 * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m ceo_agent.ceo_worker >> logs/ceo_worker.log 2>&1

On-demand:
  python3 -m ceo_agent.ceo_worker --type on_demand --hours 12
"""

import os
import sys
import json
import logging
import argparse
import urllib.request
from datetime import datetime, timezone

# Load .env
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
logger = logging.getLogger('CeoWorker')

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')

BRIEFING_HOURS    = int(os.getenv('CEO_BRIEFING_HOURS', '24'))
MIN_UPDATES       = int(os.getenv('CEO_MIN_UPDATES', '1'))
TELEGRAM_ENABLED  = os.getenv('CEO_TELEGRAM_ENABLED', 'true').lower() == 'true'
EMAIL_ENABLED     = os.getenv('SCHEDULER_EMAIL_ENABLED', 'false').lower() == 'true'


def _send_telegram(briefing: dict) -> None:
    """Send executive briefing — only if it has blockers or recommended actions."""
    if not TELEGRAM_ENABLED:
        return
    blockers = briefing.get('blockers') or []
    updates  = briefing.get('top_updates') or []
    actions  = briefing.get('recommended_actions') or []

    # Silence: no blockers, no actions = nothing CEO-worthy to say
    if not blockers and not actions:
        logger.info("CEO briefing suppressed — no blockers or recommended actions")
        return

    lines = [f'<b>Nexus Executive Brief</b>', f"<i>{briefing.get('headline', '')}</i>", '']

    if blockers:
        lines.append('<b>🚨 Blockers</b>')
        for b in blockers[:3]:
            lines.append(f"• {b.get('description', '')[:120]}")
        lines.append('')

    if updates:
        lines.append('<b>📋 Top Updates</b>')
        for u in updates[:4]:
            cid = f" [{u['client_id'][:8]}]" if u.get('client_id') else ''
            lines.append(f"• {u['agent']}{cid}: {u['text'][:100]}")
        lines.append('')

    if actions:
        lines.append('<b>✅ Recommended Actions</b>')
        for a in actions[:3]:
            lines.append(f"• {a.get('action', '')[:100]}")

    text     = '\n'.join(lines)
    severity = 'critical' if blockers else 'summary'
    try:
        from lib.hermes_gate import send as gate_send
        gate_send(text, event_type='executive_brief', severity=severity)
    except Exception as e:
        logger.warning(f"HermesGate send failed: {e}")


def _send_email(briefing: dict) -> None:
    if not EMAIL_ENABLED:
        return
    try:
        from notifications.operator_notifications import send_operator_email

        blockers = briefing.get('blockers') or []
        updates  = briefing.get('top_updates') or []
        actions  = briefing.get('recommended_actions') or []

        lines = [
            "Nexus Executive Brief",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Headline: {briefing.get('headline', '')}",
            "",
        ]
        if blockers:
            lines.append("Blockers:")
            for b in blockers:
                lines.append(f"- {b.get('description', '')}")
            lines.append("")
        if updates:
            lines.append("Top Updates:")
            for u in updates:
                cid = f" [{u['client_id'][:8]}]" if u.get('client_id') else ''
                lines.append(f"- {u['agent']}{cid}: {u['text']}")
            lines.append("")
        if actions:
            lines.append("Recommended Actions:")
            for a in actions:
                lines.append(f"- {a.get('action', '')}")
            lines.append("")

        send_operator_email(
            subject="Nexus Executive Brief",
            body="\n".join(lines),
        )
    except Exception as e:
        logger.warning(f"CEO email: {e}")


def _send_telegram_text(text: str, event_type: str = 'ceo_report', severity: str = 'summary') -> None:
    """Send raw CEO text — routes through gate, max once per 12h per event_type."""
    if not TELEGRAM_ENABLED:
        return
    try:
        from lib.hermes_gate import send as gate_send
        gate_send(text, event_type=event_type, severity=severity)
    except Exception as e:
        logger.warning(f"HermesGate text send failed: {e}")


def run_hourly_health_check() -> None:
    """Hourly: system status snapshot — workers, error count, queue depth."""
    from monitoring.monitoring_worker import run_checks
    result = run_checks()
    alerts = result.get('alerts', [])

    lines = ['<b>Nexus Hourly Health Check</b>']
    lines.append(f"Workers stale: {len(result.get('stale_workers', []))}")
    lines.append(f"Signals queue: {result['queue']['signals_pending']}")
    lines.append(f"Errors (15m): {result['errors_15m']}")
    lines.append(f"AI cost today: ${result['ai_cost_today']:.2f}")

    if alerts:
        lines.append('')
        lines.append('<b>⚠ Active Alerts:</b>')
        for a in alerts:
            lines.append(f"  • {a}")
        # Only send hourly health if there are actual alerts
        _send_telegram_text('\n'.join(lines), event_type='hourly_health', severity='warning')
    else:
        # No alerts → no message (silence is correct)
        logger.info("Hourly health check: all clear — no message sent")


def run_daily_ceo_report() -> None:
    """Daily: revenue, leads, grants, funding pipeline, blockers."""
    lines = ['<b>🏆 Daily CEO Report</b>',
             f"<i>{datetime.now(timezone.utc).strftime('%B %d, %Y')}</i>", '']

    try:
        from ceo_agent.revenue_tracker import build_revenue_summary_text
        lines.append(f"💰 Revenue: {build_revenue_summary_text()}")
    except Exception as e:
        lines.append(f"💰 Revenue: unavailable ({e})")

    try:
        from ceo_agent.lead_tracker import build_lead_summary_text
        lines.append(f"🎯 Leads: {build_lead_summary_text()}")
    except Exception as e:
        lines.append(f"🎯 Leads: unavailable ({e})")

    try:
        from ceo_agent.autofix_service import run_safe_fixes
        fixes = run_safe_fixes()
        fix_summary = ', '.join(f"{k}={v}" for k, v in fixes.items() if isinstance(v, dict) and any(v.values()))
        lines.append(f"🔧 Auto-fixes: {fix_summary or 'none needed'}")
    except Exception as e:
        lines.append(f"🔧 Auto-fixes: {e}")

    try:
        from ceo_agent.alert_engine import run_all_checks
        alerts = run_all_checks()
        lines.append(f"🚨 Alerts fired: {len(alerts)}")
    except Exception as e:
        lines.append(f"🚨 Alerts: {e}")

    # Standard briefing
    from ceo_agent.ceo_agent import run_briefing
    run_briefing(hours=24, brief_type='daily_ceo', min_updates=0)

    _send_telegram_text('\n'.join(lines), event_type='daily_ceo_report', severity='summary')


def run_weekly_ceo_report() -> None:
    """Weekly: MRR delta, lead conversion, content performance, marketing plan."""
    from ceo_agent.revenue_tracker import get_mrr, get_revenue_last_n_days
    from ceo_agent.lead_tracker import get_leads
    from ceo_agent.launch_tracker import get_week_metrics, get_content_topics, get_outreach_targets

    mrr = get_mrr()
    rev_7d = get_revenue_last_n_days(7)
    leads = get_leads(limit=200)
    won = sum(1 for l in leads if l.get('status') == 'won')
    active = sum(1 for l in leads if l.get('status') not in ('won', 'lost', 'cold'))
    conversion = round((won / len(leads) * 100) if leads else 0, 1)

    week_metrics = get_week_metrics()
    kpi_lines = []
    for m in week_metrics[:5]:
        val = float(m.get('metric_value', 0))
        tgt = m.get('target_value')
        name = m.get('metric_name', '?')
        kpi_lines.append(f"  {name}: {val:.1f}" + (f" / {float(tgt):.1f}" if tgt else ''))

    lines = [
        '<b>📊 Weekly CEO Report</b>',
        f"<i>Week of {datetime.now(timezone.utc).strftime('%B %d, %Y')}</i>",
        '',
        f"💰 MRR: ${mrr:,.2f} | Revenue 7d: ${rev_7d:,.2f}",
        f"🎯 Leads: {len(leads)} total | {active} active | {won} won ({conversion}% CVR)",
    ]

    if kpi_lines:
        lines.append('\n<b>Launch KPIs:</b>')
        lines.extend(kpi_lines)

    lines.append('\n' + get_content_topics(3))
    lines.append('\n' + get_outreach_targets(2))

    _send_telegram_text('\n'.join(lines)[:4000], event_type='weekly_ceo_report', severity='summary')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', default='periodic',
                        choices=['periodic', 'on_demand', 'critical',
                                 'hourly_health', 'daily_ceo', 'weekly_ceo'])
    parser.add_argument('--hours', type=int, default=BRIEFING_HOURS)
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info(f"CEO worker starting type={args.type} hours={args.hours}")

    from monitoring.heartbeat_service import send_heartbeat
    send_heartbeat('ceo_worker', 'running')

    if args.type == 'hourly_health':
        run_hourly_health_check()
    elif args.type == 'daily_ceo':
        run_daily_ceo_report()
    elif args.type == 'weekly_ceo':
        run_weekly_ceo_report()
    else:
        from ceo_agent.ceo_agent import run_briefing
        briefing_id = run_briefing(
            hours=args.hours,
            brief_type=args.type,
            min_updates=MIN_UPDATES,
        )

        if briefing_id:
            from ceo_agent.briefing_service import get_latest_briefing
            briefing = get_latest_briefing()
            if briefing:
                _send_telegram(briefing)
                _send_email(briefing)
            logger.info(f"CEO briefing complete: {briefing_id}")
        else:
            logger.info("No briefing generated (insufficient activity)")

    send_heartbeat('ceo_worker', 'idle')
    logger.info("CEO worker done.")


if __name__ == '__main__':
    main()
