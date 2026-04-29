#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.model_router import provider_summary
from scripts.prelaunch_utils import (
    count_by,
    count_rows,
    default_test_mode,
    list_launchd,
    pgrep_lines,
    probe_port,
    rest_select,
)


def recent_errors(limit: int = 10) -> list[dict]:
    rows = rest_select(
        "system_events?select=id,event_type,status,last_error,updated_at"
        "&last_error=not.is.null"
        "&order=updated_at.desc"
        f"&limit={limit}"
    ) or []
    return rows


def main() -> int:
    telegram_processes = pgrep_lines("telegram_bot.py|hermes_status_bot.py|hermes_claude_bot.py")
    scheduler_processes = pgrep_lines("operations_center/scheduler.py")
    orchestrator_processes = pgrep_lines("services/nexus-orchestrator/src/index.js")

    report = {
        "test_mode_default": default_test_mode(),
        "services": {
            "control_center": probe_port("127.0.0.1", 4000),
            "netcup_ollama_tunnel": probe_port("127.0.0.1", 11555),
            "scheduler_processes": scheduler_processes,
            "orchestrator_processes": orchestrator_processes,
            "telegram_processes": telegram_processes,
            "email_pipeline_loaded": any("email-pipeline" in line for line in list_launchd()),
        },
        "launchd": list_launchd(),
        "model_router": provider_summary(),
        "supabase": {
            "system_events_total": count_rows("system_events"),
            "job_queue_total": count_rows("job_queue"),
            "workflow_outputs_total": count_rows("workflow_outputs"),
            "worker_heartbeats_total": count_rows("worker_heartbeats"),
            "job_queue_by_status": count_by("job_queue", "status"),
            "system_events_by_type": count_by("system_events", "event_type"),
            "workflow_outputs_by_status": count_by("workflow_outputs", "status"),
            "worker_heartbeats": rest_select(
                "worker_heartbeats?select=worker_id,worker_type,status,last_seen_at"
                "&order=last_seen_at.desc&limit=10"
            ) or [],
            "recent_errors": recent_errors(),
        },
        "flags": {
            "scheduler_email_enabled": os.getenv("SCHEDULER_EMAIL_ENABLED", "false"),
            "scheduler_telegram_enabled": os.getenv("SCHEDULER_TELEGRAM_ENABLED", "true"),
            "telegram_email_summaries_enabled": os.getenv("TELEGRAM_EMAIL_SUMMARIES_ENABLED", "false"),
            "enable_ceo_routed_workers": os.getenv("ENABLE_CEO_ROUTED_WORKERS", "false"),
            "hermes_fallback_enabled": os.getenv("HERMES_FALLBACK_ENABLED", "false"),
        },
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
