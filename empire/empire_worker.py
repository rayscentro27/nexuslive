"""
Empire Worker.

Weekly empire state summary sent to Telegram.
Generates reinvestment recommendations from current revenue.

Cron: 0 10 * * 1  (Mondays at 10am)

Run: python3 -m empire.empire_worker
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14

logger = logging.getLogger('EmpireWorker')


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
        body = json.dumps({'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}).encode()
        req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def run_empire_briefing() -> dict:
    from empire.empire_service import (
        get_empire_state, get_reinvestment_recommendation,
        get_top_expansion_regions,
    )

    state    = get_empire_state()
    monthly  = state.get('monthly_revenue', 0)
    all_time = state.get('all_time_revenue', 0)
    wf       = state.get('workforce', {})
    entities = state.get('entities', [])
    regions  = state.get('top_regions', [])
    capital  = state.get('capital', {})

    reinvest = get_reinvestment_recommendation(monthly)

    entity_lines = '\n'.join(
        f"  • {e.get('name','?')} ({e.get('entity_type','?')})"
        for e in entities[:5]
    ) or '  (none registered)'

    region_lines = '\n'.join(
        f"  #{i+1}  {r.get('region_name','?')} — score {r.get('total_score',0):.0f}"
        for i, r in enumerate(regions)
    ) or '  (none scored)'

    reinvest_lines = '\n'.join(
        f"  {k.title()}: ${v:,.0f}"
        for k, v in reinvest.get('recommendation', {}).items()
    )

    message = (
        f"<b>🏛 Nexus Empire Briefing</b>\n"
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} (Weekly)\n\n"
        f"Monthly Revenue: <b>${monthly:,.2f}</b>\n"
        f"All-Time Revenue: ${all_time:,.2f}\n"
        f"Capital Deployed ({state.get('period','')}): ${capital.get('total',0):,.2f}\n\n"
        f"<b>Workforce:</b> {wf.get('total_members',0)} members  "
        f"capacity={wf.get('total_capacity',0)}\n\n"
        f"<b>Entities:</b>\n{entity_lines}\n\n"
        f"<b>Top Expansion Regions:</b>\n{region_lines}\n\n"
        f"<b>Reinvestment Recommendation (${monthly:,.0f}/mo):</b>\n"
        f"{reinvest_lines}\n\n"
        f"<i>All capital moves require manual approval.</i>"
    )
    _send_telegram(message)
    logger.info(f"Empire briefing sent: monthly=${monthly}")
    return state


if __name__ == '__main__':
    _load_env()
    logging.basicConfig(level=logging.INFO)
    run_empire_briefing()
