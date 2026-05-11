#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.prelaunch_utils import count_by, count_rows, default_test_mode, pgrep_lines, probe_port


def str_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def simulate_users(count: int) -> dict:
    rng = random.Random(42)
    durations = []
    jobs_completed = 0
    jobs_failed = 0
    errors: dict[str, int] = {}
    for _ in range(count):
        for step in ("login", "onboarding", "credit_analysis", "business_setup", "funding_roadmap", "hermes_command"):
            ok = rng.random() > (0.03 if step in {"login", "onboarding"} else 0.08)
            durations.append(round(rng.uniform(0.2, 2.8), 3))
            if ok:
                jobs_completed += 1
            else:
                jobs_failed += 1
                errors[step] = errors.get(step, 0) + 1
    return {
        "events_created": count * 6,
        "jobs_created": count * 6,
        "jobs_completed": jobs_completed,
        "jobs_failed": jobs_failed,
        "average_processing_time": round(statistics.mean(durations), 3) if durations else 0,
        "errors_by_type": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", nargs="?", const="true", default="true")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--send-email", nargs="?", const="false", default="false")
    parser.add_argument("--send-telegram", nargs="?", const="false", default="false")
    parser.add_argument("--create-real-users", nargs="?", const="false", default="false")
    args = parser.parse_args()

    dry_run = str_bool(args.dry_run, True)
    send_email = str_bool(args.send_email, False)
    send_telegram = str_bool(args.send_telegram, False)
    create_real_users = str_bool(args.create_real_users, False)

    summary = simulate_users(args.count)
    report = {
        "dry_run": dry_run,
        "requested_count": args.count,
        "test_mode_default": default_test_mode(),
        "notifications": {
            "send_email": send_email,
            "send_telegram": send_telegram,
            "create_real_users": create_real_users,
        },
        "runtime_checks": {
            "control_center_up": probe_port("127.0.0.1", 4000),
            "scheduler_running": bool(pgrep_lines("operations_center/scheduler.py")),
            "orchestrator_running": bool(pgrep_lines("services/nexus-orchestrator/src/index.js")),
            "job_queue_backlog": count_by("job_queue", "status"),
            "worker_heartbeat_status": count_by("worker_heartbeats", "status"),
            "system_events_total": count_rows("system_events"),
            "workflow_outputs_total": count_rows("workflow_outputs"),
        },
        "simulation": {
            "total_simulated_users": args.count,
            **summary,
            "queue_backlog": count_rows("job_queue", "status=neq.completed"),
        },
        "notes": [
            "No real users, charges, Telegram messages, or emails were created in dry-run mode.",
            "This harness simulates user journeys and pressure against current worker/queue assumptions.",
        ],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
