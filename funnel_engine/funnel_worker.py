"""
Funnel Automation Worker.

Polls system_events for lifecycle events and:
  1. Records funnel_events
  2. Advances funnel_stage_tracking
  3. Triggers automated follow-ups for stalled clients

Event → Stage map:
  lead_inquiry          → lead_captured
  client_registered     → onboarding_started
  onboarding_complete   → credit_improved (triggers credit agent)
  credit_analysis_done  → credit_improved
  funding_submitted     → funding_applied
  funding_approved      → funding_received
  capital_deployed      → capital_allocated

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m funnel_engine.funnel_worker

Or via cron (every 15 minutes):
  */15 * * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m funnel_engine.funnel_worker >> logs/funnel_worker.log 2>&1
"""

import os
import sys
import json
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
logger = logging.getLogger('FunnelWorker')

# Map system_event event_type → funnel stage
EVENT_STAGE_MAP = {
    'lead_inquiry':            'lead_captured',
    'lead_qualified':          'lead_captured',
    'client_registered':       'onboarding_started',
    'onboarding_complete':     'credit_improved',
    'credit_analysis_done':    'credit_improved',
    'credit_analysis_completed': 'credit_improved',
    'funding_submitted':       'funding_applied',
    'funding_approved':        'funding_received',
    'funding_received':        'funding_received',
    'capital_deployed':        'capital_allocated',
}

# How long (days) a client can stay at a stage before we nudge them
STALL_THRESHOLDS = {
    'lead_captured':     3,
    'onboarding_started': 2,
    'credit_improved':   7,
    'funding_applied':   10,
    'funding_received':  5,
    'capital_allocated': 30,
}

STALL_MESSAGES = {
    'onboarding_started': (
        "Hi! Just checking in — it looks like you haven't completed your onboarding yet. "
        "It only takes a few minutes to finish. Reply 'next' to continue where you left off."
    ),
    'credit_improved': (
        "Quick update: our team is reviewing your credit profile. "
        "If you have any questions or want to provide additional documents, just reply here."
    ),
    'funding_applied': (
        "Your funding application is in review. "
        "Most lenders respond within 3–7 business days. "
        "We'll update you as soon as we have news!"
    ),
}


def _send_telegram(client_id: str, message: str) -> None:
    try:
        from autonomy.output_service import send_message
        send_message(message=message, client_id=client_id,
                     metadata={'agent': 'funnel_worker', 'type': 'nudge'})
    except Exception as e:
        logger.warning(f"Send message failed for {client_id}: {e}")


def process_lifecycle_events(limit: int = 50) -> int:
    """
    Pull recent system_events and advance funnel stages accordingly.
    Returns count of stage advances.
    """
    import urllib.request
    key = os.getenv('SUPABASE_KEY', '')
    url = (
        f"{os.getenv('SUPABASE_URL', '')}/rest/v1/system_events"
        f"?status=eq.pending&event_type=in.({','.join(EVENT_STAGE_MAP.keys())})"
        f"&order=created_at.asc&limit={limit}&select=*"
    )
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            events = json.loads(r.read())
    except Exception as e:
        logger.warning(f"Could not fetch system_events: {e}")
        return 0

    from funnel_engine.funnel_service import record_funnel_event, update_funnel_stage

    advanced = 0
    for event in events:
        event_type = event.get('event_type', '')
        client_id  = event.get('client_id')
        payload    = event.get('payload') or {}
        lead_id    = payload.get('lead_id')

        stage = EVENT_STAGE_MAP.get(event_type)
        if not stage:
            continue

        record_funnel_event(
            stage=stage,
            client_id=client_id,
            lead_id=lead_id,
            event_source=event_type,
            metadata=payload,
        )

        if client_id:
            if update_funnel_stage(client_id, stage):
                advanced += 1

    return advanced


def nudge_stalled_clients() -> int:
    """Send follow-up messages to clients stalled at a stage. Returns nudge count."""
    from funnel_engine.funnel_service import get_stalled_clients

    nudged = 0
    for stage, days in STALL_THRESHOLDS.items():
        msg = STALL_MESSAGES.get(stage)
        if not msg:
            continue
        stalled = get_stalled_clients(days=days)
        for client in stalled:
            if client.get('current_stage') != stage:
                continue
            client_id = client.get('client_id', '')
            if not client_id:
                continue
            _send_telegram(client_id, msg)
            nudged += 1
            logger.info(f"Nudge sent: client={client_id} stage={stage}")

    return nudged


def log_funnel_summary() -> None:
    """Log and send funnel stage report."""
    from funnel_engine.funnel_service import get_stage_report
    report = get_stage_report()
    lines  = [f"  {stage}: {count}" for stage, count in report.items()]
    logger.info("Funnel stage report:\n" + '\n'.join(lines))

    total = sum(report.values())
    if total > 0:
        try:
            from autonomy.summary_service import write_summary
            write_summary(
                agent_name='funnel_worker',
                summary_type='funnel_report',
                summary_text=f"Funnel: {total} total clients tracked across stages",
                what_happened=f"Funnel stage counts: {report}",
                what_changed='Funnel stages updated from lifecycle events',
                recommended_next_action=(
                    'Review stalled clients and consider escalating high-value leads'
                ),
                priority='low',
            )
        except Exception:
            pass


def main() -> None:
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    from monitoring.heartbeat_service import send_heartbeat
    send_heartbeat('funnel_worker', 'running')

    logger.info("Funnel worker starting")

    advanced = process_lifecycle_events()
    nudged   = nudge_stalled_clients()
    log_funnel_summary()

    send_heartbeat('funnel_worker', 'idle')
    logger.info(f"Funnel worker done. advanced={advanced} nudged={nudged}")


if __name__ == '__main__':
    main()
