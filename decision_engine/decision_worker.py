"""
Decision Engine Worker.

Runs the autonomous decision cycle on a schedule.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m decision_engine.decision_worker

Or via cron (every 30 minutes):
  */30 * * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m decision_engine.decision_worker >> \\
      logs/decision_worker.log 2>&1
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
logger = logging.getLogger('DecisionWorker')


def main() -> None:
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    from monitoring.heartbeat_service import send_heartbeat
    send_heartbeat('decision_worker', 'running')

    logger.info("Decision worker starting")

    from decision_engine.decision_engine import run_decision_cycle, get_pending_decisions

    result = run_decision_cycle()
    pending = get_pending_decisions(limit=10)

    logger.info(
        f"Decision cycle complete: stored={result['stored']} "
        f"executed={result['executed']} held={result['held']}"
    )

    # Alert if decisions are piling up waiting for approval
    if len(pending) >= 5:
        try:
            from lib.hermes_gate import send as gate_send
            lines = [f"• {d['decision_type']}: {d['action'][:60]}" for d in pending[:5]]
            msg = (
                f"<b>Nexus Decisions Awaiting Approval</b>\n"
                f"{len(pending)} pending decision(s):\n"
                + '\n'.join(lines)
                + "\n\nUse <code>approve_decision(id)</code> to release."
            )
            gate_send(msg, event_type='critical_alert', severity='critical')
        except Exception as e:
            logger.warning(f"Telegram alert failed: {e}")

    # Write summary
    if result['stored'] > 0:
        try:
            from autonomy.summary_service import write_summary
            write_summary(
                agent_name='decision_worker',
                summary_type='decision_cycle',
                summary_text=(
                    f"Decision cycle: {result['stored']} decision(s) generated, "
                    f"{result['executed']} executed, {result['held']} held for approval"
                ),
                what_happened='Autonomous decision rules evaluated',
                what_changed=f"{result['executed']} auto-decisions executed",
                recommended_next_action=(
                    f"Review {result['held']} held decision(s) in decisions table"
                    if result['held'] else 'No action required'
                ),
                follow_up_needed=(result['held'] > 0),
                priority='high' if result['held'] > 3 else 'low',
            )
        except Exception:
            pass

    send_heartbeat('decision_worker', 'idle')
    logger.info("Decision worker done")


if __name__ == '__main__':
    main()
