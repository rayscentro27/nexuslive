"""
Nexus One Worker.

Orchestrates the full Nexus One executive intelligence cycle.

Modes:
  brief   — daily executive brief (6am)
  check   — on-demand status check
  alert   — critical alert scan (every 30 min)
  ready   — readiness check
  command — process a plain-language command (from Telegram handler)

Cron:
  0 6 * * *      — daily brief
  */30 * * * *   — critical alert scan
  (on-demand)    — command interpretation, readiness check

Run:
  python3 -m nexus_one.nexus_one_worker brief
  python3 -m nexus_one.nexus_one_worker check
  python3 -m nexus_one.nexus_one_worker alert
  python3 -m nexus_one.nexus_one_worker ready
  python3 -m nexus_one.nexus_one_worker command "add youtube channel @MacroAlf"
"""

import os
import sys
import json
import logging
import urllib.request
from datetime import datetime, timezone
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14

logger = logging.getLogger('NexusOneWorker')


def _load_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())


def _send_telegram(message: str) -> None:
    token   = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return
    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({
            'chat_id':    chat_id,
            'text':       message,
            'parse_mode': 'HTML',
        }).encode()
        req = urllib.request.Request(
            url, data=body, headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def _store_briefing(brief_text: str, brief_type: str, urgency: str) -> None:
    """Persist briefing to executive_briefings table."""
    key = os.getenv('SUPABASE_KEY', '')
    url = f"{os.getenv('SUPABASE_URL', '')}/rest/v1/executive_briefings"
    row = {
        'briefing_type': brief_type,
        'content':       brief_text,
        'urgency':       urgency,
        'generated_by':  'nexus_one',
    }
    data = json.dumps(row).encode()
    h    = {
        'apikey': key, 'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json', 'Prefer': 'return=minimal',
    }
    try:
        req = urllib.request.Request(url, data=data, headers=h, method='POST')
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Briefing store failed: {e}")


# ─── Mode handlers ─────────────────────────────────────────────────────────────

def run_daily_brief() -> None:
    from nexus_one.reporting_layer import daily_brief, what_changed
    from nexus_one.output_formatter import format_daily_summary

    brief   = daily_brief()
    changed = what_changed(hours=24)
    text    = format_daily_summary(brief, changed)

    _send_telegram(text)
    _store_briefing(text, brief_type='daily', urgency=brief.get('urgency', 'low'))
    logger.info(f"Daily brief sent: urgency={brief.get('urgency')}")


def run_attention_check() -> None:
    from nexus_one.reporting_layer import attention_required
    from nexus_one.output_formatter import format_attention_required

    attention = attention_required()
    text      = format_attention_required(attention)
    _send_telegram(text)
    logger.info(f"Attention check: {attention.get('total_items')} items")


def run_critical_alert_scan() -> None:
    from nexus_one.reporting_layer import critical_alerts
    from nexus_one.output_formatter import format_critical_alert

    alerts = critical_alerts()
    if not alerts:
        logger.info("Alert scan: all clear")
        return

    for alert in alerts[:3]:
        text = format_critical_alert(
            issue=alert.get('issue', 'Unknown issue'),
            impact='Pipeline or revenue may be affected',
            recommended_action='Review in Nexus One dashboard or reply with a command',
            urgency=alert.get('urgency', 'high'),
        )
        _send_telegram(text)
    logger.info(f"Alert scan: {len(alerts)} alerts sent")


def run_readiness_check() -> None:
    from nexus_one.readiness_checker import run_readiness_check, format_readiness_report

    report = run_readiness_check()
    text   = format_readiness_report(report)
    _send_telegram(text)
    logger.info(f"Readiness check: {report.get('overall')}")


def run_command(command_text: str) -> None:
    from nexus_one.command_interpreter import handle_telegram_command

    text = handle_telegram_command(command_text, operator_id='super_admin')
    _send_telegram(text)
    logger.info(f"Command processed: {command_text[:60]}")


def run_executive_brief() -> None:
    """Full executive brief (deeper than daily summary)."""
    from nexus_one.reporting_layer import daily_brief
    from nexus_one.output_formatter import format_executive_brief

    brief = daily_brief()
    text  = format_executive_brief(brief)
    _send_telegram(text)
    _store_briefing(text, brief_type='executive', urgency=brief.get('urgency', 'low'))
    logger.info(f"Executive brief sent")


# ─── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    _load_env()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    mode    = sys.argv[1] if len(sys.argv) > 1 else 'brief'
    payload = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''

    MODE_HANDLERS = {
        'brief':   run_daily_brief,
        'exec':    run_executive_brief,
        'check':   run_attention_check,
        'alert':   run_critical_alert_scan,
        'ready':   run_readiness_check,
    }

    if mode == 'command' and payload:
        run_command(payload)
    elif mode in MODE_HANDLERS:
        MODE_HANDLERS[mode]()
    else:
        print(f"Usage: python3 -m nexus_one.nexus_one_worker [brief|exec|check|alert|ready|command <text>]")
        sys.exit(1)
