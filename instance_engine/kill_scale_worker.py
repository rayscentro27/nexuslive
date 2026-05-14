"""
Kill / Scale Worker.

Standalone cron runner for kill/scale analysis.
The portfolio_worker also calls run_kill_scale_analysis() daily,
so this worker is optional — use it for more frequent checks.

Cron: 0 */6 * * *  (every 6 hours)

Run: python3 -m instance_engine.kill_scale_worker
"""

import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger('KillScaleWorker')


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
    from lib.telegram_notification_policy import should_send_telegram_notification
    from lib.hermes_gate import send as gate_send

    allowed, _ = should_send_telegram_notification("worker_summary")
    if not allowed:
        return
    gate_send(message, event_type="worker_summary", severity="summary")


def run() -> None:
    from instance_engine.kill_scale_engine import (
        run_kill_scale_analysis, get_pending_decisions,
    )

    # Run analysis
    new_decisions = run_kill_scale_analysis()

    # Count all pending decisions
    all_pending = get_pending_decisions(limit=50)
    total_pending = len(all_pending)

    scale_count = sum(1 for d in all_pending if d.get('decision') == 'scale')
    kill_count  = sum(1 for d in all_pending if d.get('decision') == 'kill')
    hold_count  = sum(1 for d in all_pending if d.get('decision') == 'hold')

    if new_decisions or total_pending > 0:
        new_lines = '\n'.join(
            f"  [{d.get('decision','?').upper()}] {d.get('reason','')[:80]}"
            for d in new_decisions[:5]
        ) or '  (no new decisions this cycle)'

        message = (
            f"<b>⚡ Kill/Scale Engine</b>\n"
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n\n"
            f"New this cycle: <b>{len(new_decisions)}</b>\n"
            f"Total pending:  <b>{total_pending}</b> "
            f"(scale={scale_count} kill={kill_count} hold={hold_count})\n\n"
            f"<b>New decisions:</b>\n{new_lines}\n\n"
            f"Use <code>/approve &lt;id&gt;</code> or <code>/override &lt;id&gt;</code> to act."
        )
        _send_telegram(message)

    logger.info(
        f"Kill/Scale cycle: {len(new_decisions)} new, {total_pending} total pending"
    )


if __name__ == '__main__':
    _load_env()
    logging.basicConfig(level=logging.INFO)
    run()
