"""
Scheduler Worker.

Polls source_schedules for due entries and fires source_scan_queued events.

Safety:
  - Idempotency key derived from source_id + scheduled run time bucket
    prevents duplicate events if the worker overlaps or restarts.
  - Advances schedule immediately before emitting to prevent double-fire
    if the process is killed mid-run.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m source_scheduling.scheduler_worker

Or via cron (every 5 minutes):
  */5 * * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m source_scheduling.scheduler_worker >> \\
      logs/scheduler_worker.log 2>&1
"""

import os
import sys
import json
import hashlib
import logging
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
logger = logging.getLogger('SchedulerWorker')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
MAX_DUE      = int(os.getenv('SCHEDULER_MAX_DUE', '20'))


def _make_idempotency_key(source_id: str, next_run_at: str) -> str:
    """
    Stable key for one scheduled run of a source.
    Hashed from source_id + the scheduled run time, truncated to minute.
    """
    bucket = (next_run_at or '')[:16]  # 'YYYY-MM-DDTHH:MM'
    raw    = f"sched_scan_{source_id}_{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_source_details(source_id: str) -> dict:
    """Fetch label/type/domain for a source_id."""
    import urllib.request
    key  = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/research_sources?id=eq.{source_id}&select=label,source_type,domain,priority&limit=1"
    req  = urllib.request.Request(url, headers={
        'apikey': key, 'Authorization': f'Bearer {key}'
    })
    try:
        import json as _json
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = _json.loads(r.read())
            return rows[0] if rows else {}
    except Exception:
        return {}


def run_scheduler() -> int:
    """
    Fire events for all due schedules.
    Returns the number of sources queued.
    """
    from source_scheduling.schedule_service import get_due_schedules, advance_schedule
    from autonomy.event_emitter import emit_event

    due     = get_due_schedules(limit=MAX_DUE)
    queued  = 0
    skipped = 0

    logger.info(f"Scheduler: {len(due)} schedule(s) due")

    for sched in due:
        source_id    = sched.get('source_id')
        schedule_id  = sched.get('id')
        schedule_type = sched.get('schedule_type', 'daily')
        interval_min  = sched.get('interval_minutes')
        next_run_at   = sched.get('next_run_at', '')

        if not source_id:
            continue

        ikey    = _make_idempotency_key(source_id, next_run_at)
        details = _get_source_details(source_id)

        # Advance schedule FIRST — prevents double-fire if process dies after emit
        advanced = advance_schedule(schedule_id, schedule_type, interval_min)
        if not advanced:
            logger.warning(f"Could not advance schedule {schedule_id}, skipping emit")
            skipped += 1
            continue

        # Emit scan event (idempotency key prevents duplicate processing)
        event_id = emit_event(
            event_type='source_scan_queued',
            client_id=None,
            payload={
                'source_id':    source_id,
                'source_type':  details.get('source_type', 'unknown'),
                'source_url':   '',
                'label':        details.get('label', source_id[:8]),
                'domain':       details.get('domain', ''),
                'priority':     details.get('priority', 'medium'),
                'trigger':      'scheduler',
                'schedule_type': schedule_type,
            },
            idempotency_key=ikey,
        )

        if event_id:
            logger.info(
                f"Queued: source={source_id} label={details.get('label','')} "
                f"schedule={schedule_type}"
            )
            queued += 1
        else:
            logger.debug(f"Skipped (duplicate or error): source={source_id}")
            skipped += 1

    logger.info(f"Scheduler done: queued={queued} skipped={skipped}")
    return queued


def run_policy_escalations() -> None:
    """Escalate priority for stale sources once per worker run."""
    try:
        from source_scheduling.policy_service import escalate_stale_priorities
        escalated = escalate_stale_priorities()
        if escalated:
            logger.info(f"Priority escalated for {len(escalated)} stale source(s)")
    except Exception as e:
        logger.warning(f"Policy escalation failed: {e}")


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info("Scheduler worker starting")

    from monitoring.heartbeat_service import send_heartbeat
    send_heartbeat('scheduler_worker', 'running')

    queued = run_scheduler()
    run_policy_escalations()

    send_heartbeat('scheduler_worker', 'idle')
    logger.info(f"Scheduler worker done. Queued: {queued}")


if __name__ == '__main__':
    main()
