"""
Autonomy Worker — main loop.

Polls system_events and dispatches to the agent registry every
POLL_INTERVAL seconds.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m autonomy.autonomy_worker

Or via launchd / cron (every minute):
  * * * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m autonomy.autonomy_worker >> logs/autonomy_worker.log 2>&1
"""

import os
import sys
import time
import logging

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
logger = logging.getLogger('AutonomyWorker')

from autonomy.event_dispatcher import run_dispatch_cycle
from monitoring.heartbeat_service import send_heartbeat
from monitoring.job_tracker import record_job_start, record_job_complete, record_job_fail

SUPABASE_URL   = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY   = os.getenv('SUPABASE_KEY', '')
POLL_INTERVAL  = int(os.getenv('AUTONOMY_POLL_INTERVAL', '30'))
RUN_ONCE       = os.getenv('AUTONOMY_RUN_ONCE', 'false').lower() == 'true'


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info(f"Autonomy worker starting (poll_interval={POLL_INTERVAL}s)")
    send_heartbeat('autonomy_worker', 'running')

    while True:
        job_id = record_job_start('autonomy_worker', 'dispatch_cycle')
        t0     = time.time()
        try:
            result = run_dispatch_cycle()
            duration = int((time.time() - t0) * 1000)
            logger.info(
                f"Dispatch cycle: processed={result['processed']} "
                f"acted={result.get('acted', 0)} "
                f"ignored={result.get('ignored', 0)} "
                f"duration={duration}ms"
            )
            record_job_complete(job_id, duration, meta=result)
        except Exception as exc:
            duration = int((time.time() - t0) * 1000)
            logger.exception("Dispatch cycle error")
            record_job_fail(job_id, str(exc), duration)

        send_heartbeat('autonomy_worker', 'idle')

        if RUN_ONCE:
            break
        time.sleep(POLL_INTERVAL)

    logger.info("Autonomy worker done.")


if __name__ == '__main__':
    main()
