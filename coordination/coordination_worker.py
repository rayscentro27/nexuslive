"""
Coordination Worker.

Runs periodically to:
  1. Detect stale handoffs (agent_handoff events stuck in pending > threshold)
  2. Log action summary for observability
  3. Clean up expired cooldown states in agent_context
  4. Alert on conflict/coordination anomalies via Telegram

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m coordination.coordination_worker

Or via cron (every 15 minutes):
  */15 * * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m coordination.coordination_worker >> \\
      logs/coordination_worker.log 2>&1
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

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
logger = logging.getLogger('CoordinationWorker')

from coordination.action_history import get_action_summary
from monitoring.heartbeat_service import send_heartbeat

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')
TELEGRAM_ENABLED   = os.getenv('COORD_TELEGRAM_ENABLED', 'true').lower() == 'true'
EMAIL_ENABLED      = os.getenv('SCHEDULER_EMAIL_ENABLED', 'false').lower() == 'true'

STALE_HANDOFF_MINUTES = int(os.getenv('COORD_STALE_HANDOFF_MINUTES', '60'))
ALERT_SKIP_RATIO      = float(os.getenv('COORD_ALERT_SKIP_RATIO', '0.8'))


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 400 and path.startswith("system_events?event_type=eq.agent_handoff"):
            logger.info("GET stale handoffs → unsupported on this system_events schema")
            return []
        if e.code == 404:
            logger.info(f"GET {path} → optional table/view not present")
            return []
        logger.warning(f"GET {path} → HTTP {e.code}")
        return []
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _send_telegram(text: str) -> None:
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    body = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            pass
    except Exception as e:
        logger.warning(f"Telegram: {e}")


def _send_email(subject: str, body: str) -> None:
    if not EMAIL_ENABLED:
        return
    try:
        from notifications.operator_notifications import send_operator_email
        sent, detail = send_operator_email(subject, body)
        if not sent:
            logger.warning(f"Coordination email skipped/failed: {detail}")
    except Exception as e:
        logger.warning(f"Coordination email: {e}")


def _notify_dual(brief_text: str, email_subject: str, email_body: str) -> None:
    _send_telegram(brief_text)
    _send_email(email_subject, email_body)


# ─── Checks ───────────────────────────────────────────────────────────────────

def check_stale_handoffs() -> list:
    """Return agent_handoff events that have been pending too long."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=STALE_HANDOFF_MINUTES)
    ).strftime('%Y-%m-%dT%H:%M:%SZ')
    cutoff_q = urllib.parse.quote(cutoff, safe='')
    try:
        return _sb_get(
            f"system_events?event_type=eq.agent_handoff"
            f"&status=eq.pending"
            f"&created_at=lt.{cutoff_q}"
            f"&select=id,client_id,payload,created_at&limit=20"
        )
    except Exception:
        logger.info("stale handoff query unsupported on this system_events schema")
        return []


def check_skip_ratio(summary: dict) -> bool:
    """Return True if skip ratio is above alert threshold."""
    total   = summary.get('total', 0)
    skipped = summary['by_action'].get('skipped', 0)
    if total < 5:
        return False
    return (skipped / total) >= ALERT_SKIP_RATIO


def sweep_expired_cooldowns() -> int:
    """
    Clear expired cooldown entries from agent_context rows.
    Returns count of clients updated.
    """
    now  = datetime.now(timezone.utc).isoformat()
    rows = _sb_get("agent_context?select=id,client_id,cooldown_state&limit=200")
    if not rows:
        return 0
    updated = 0
    for row in rows:
        cd = row.get('cooldown_state') or {}
        if isinstance(cd, str):
            try:
                cd = json.loads(cd)
            except Exception:
                continue
        cleaned = {k: v for k, v in cd.items() if v > now}
        if len(cleaned) != len(cd):
            url  = f"{SUPABASE_URL}/rest/v1/agent_context?id=eq.{row['id']}"
            body = json.dumps({'cooldown_state': cleaned, 'updated_at': now}).encode()
            req  = urllib.request.Request(url, data=body, headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal',
            }, method='PATCH')
            try:
                with urllib.request.urlopen(req, timeout=8) as _:
                    updated += 1
            except Exception:
                pass
    return updated


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info("Coordination worker starting")
    send_heartbeat('coordination_worker', 'running')

    alerts = []

    # 1. Stale handoffs
    stale = check_stale_handoffs()
    if stale:
        ids = [s.get('id', '?')[:8] for s in stale]
        alerts.append(f"STALE HANDOFFS: {len(stale)} agent_handoff events pending > {STALE_HANDOFF_MINUTES}m")
        logger.warning(f"Stale handoffs: {ids}")

    # 2. Action summary + skip ratio
    summary = get_action_summary(hours=6)
    logger.info(
        f"Action summary (6h): total={summary['total']} "
        f"by_agent={summary['by_agent']} "
        f"by_action={summary['by_action']}"
    )
    if check_skip_ratio(summary):
        skip_count = summary['by_action'].get('skipped', 0)
        alerts.append(
            f"HIGH SKIP RATIO: {skip_count}/{summary['total']} actions skipped in last 6h"
        )

    # 3. Cooldown sweep
    cleaned = sweep_expired_cooldowns()
    if cleaned:
        logger.info(f"Cleared expired cooldowns for {cleaned} client(s)")

    # 4. Alerts
    if alerts:
        msg = '<b>Nexus Coordination Alert</b>\n\n' + '\n'.join(f'⚠ {a}' for a in alerts)
        _notify_dual(
            brief_text=msg,
            email_subject=f"Nexus Coordination Alert — {len(alerts)} issue(s)",
            email_body=(
                "Nexus Coordination Alert\n\n"
                f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
                f"Alert count: {len(alerts)}\n\n"
                + "\n".join(f"- {a}" for a in alerts)
                + "\n\nAction summary (last 6h):\n"
                + json.dumps(summary, indent=2, default=str)
            ),
        )
        logger.warning(f"Alerts: {alerts}")
    else:
        logger.info("Coordination checks passed.")

    send_heartbeat('coordination_worker', 'idle')
    logger.info("Coordination worker done.")


if __name__ == '__main__':
    main()
