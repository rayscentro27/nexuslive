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
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    blockers = briefing.get('blockers') or []
    updates  = briefing.get('top_updates') or []
    actions  = briefing.get('recommended_actions') or []

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

    text = '\n'.join(lines)
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    body = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            pass
    except Exception as e:
        logger.warning(f"Telegram: {e}")


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', default='periodic',
                        choices=['periodic', 'on_demand', 'critical'])
    parser.add_argument('--hours', type=int, default=BRIEFING_HOURS)
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info(f"CEO worker starting type={args.type} hours={args.hours}")

    from monitoring.heartbeat_service import send_heartbeat
    send_heartbeat('ceo_worker', 'running')

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
