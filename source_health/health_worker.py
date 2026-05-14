"""
Source Health Worker.

Scores all active sources and sends a Telegram summary if any are critically low.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m source_health.health_worker

Or via cron (every 6 hours):
  0 */6 * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m source_health.health_worker >> \\
      logs/health_worker.log 2>&1
"""

import os
import sys
import logging

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
logger = logging.getLogger('HealthWorker')

CRITICAL_THRESHOLD = float(os.getenv('HEALTH_CRITICAL_THRESHOLD', '30'))
ALERT_THRESHOLD    = float(os.getenv('HEALTH_ALERT_THRESHOLD', '50'))


def _send_telegram(msg: str) -> None:
    from lib.telegram_notification_policy import should_send_telegram_notification
    from lib.hermes_gate import send as gate_send

    allowed, _ = should_send_telegram_notification("worker_summary")
    if not allowed:
        return
    gate_send(msg, event_type='critical_alert', severity='critical')


def main() -> None:
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    from monitoring.heartbeat_service import send_heartbeat
    send_heartbeat('health_worker', 'running')

    from source_health.health_scorer import score_all_sources, get_low_health_sources
    from source_health.duplicate_detector import run_duplicate_detection

    logger.info("Health worker starting")

    # 1. Score all sources
    scored = score_all_sources()
    logger.info(f"Scored {scored} source(s)")

    # 2. Detect duplicates
    flagged = run_duplicate_detection()
    logger.info(f"Duplicate detection: {flagged} pair(s) flagged")

    # 3. Alert on critical sources
    critical = get_low_health_sources(threshold=CRITICAL_THRESHOLD)
    low      = get_low_health_sources(threshold=ALERT_THRESHOLD)

    if critical:
        names = [r.get('source_id', '?')[:8] for r in critical[:5]]
        msg = (
            f"<b>Nexus Health Alert</b>\n"
            f"{len(critical)} source(s) critically low (score &lt; {CRITICAL_THRESHOLD}):\n"
            + '\n'.join(f"• {n}... score={r.get('score_total',0)}"
                        for n, r in zip(names, critical[:5]))
        )
        _send_telegram(msg)
        logger.warning(f"{len(critical)} critical source(s)")

    send_heartbeat('health_worker', 'idle')
    logger.info(
        f"Health worker done. scored={scored} "
        f"critical={len(critical)} low={len(low)} "
        f"duplicates_flagged={flagged}"
    )


if __name__ == '__main__':
    main()
