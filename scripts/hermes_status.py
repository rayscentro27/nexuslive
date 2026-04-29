#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.prelaunch_utils import count_by, count_rows, pgrep_lines, probe_port, rest_select


def main() -> int:
    telegram_processes = pgrep_lines("telegram_bot.py|hermes_status_bot.py|hermes_claude_bot.py")
    scheduler_processes = pgrep_lines("operations_center/scheduler.py")
    worker_rows = rest_select(
        "worker_heartbeats?select=worker_id,worker_type,status,last_seen_at"
        "&order=last_seen_at.desc&limit=5",
        timeout=8,
    ) or []
    job_counts = count_by("job_queue", "status")

    report = {
        "control_center": probe_port("127.0.0.1", 4000),
        "hermes_gateway": probe_port("127.0.0.1", 8642),
        "scheduler_running": bool(scheduler_processes),
        "telegram_process_count": len(telegram_processes),
        "job_queue_total": count_rows("job_queue"),
        "workflow_outputs_total": count_rows("workflow_outputs"),
        "worker_heartbeats_total": count_rows("worker_heartbeats"),
        "job_queue_by_status": job_counts,
        "workers": worker_rows,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
