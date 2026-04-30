#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import subprocess
import urllib.request
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.model_router import provider_summary
from lib.env_loader import load_nexus_env
from lib.telegram_role_config import (
    get_chat_config,
    get_ops_config,
    get_reports_config,
    hermes_chat_enabled,
    shared_token_detected,
)
from scripts.prelaunch_utils import (
    count_by,
    count_rows,
    default_test_mode,
    list_launchd,
    probe_port,
    rest_select,
)

load_nexus_env()


def recent_errors(limit: int = 10) -> list[dict]:
    rows = rest_select(
        "system_events?select=id,event_type,status,last_error,updated_at"
        "&last_error=not.is.null"
        "&order=updated_at.desc"
        f"&limit={limit}"
    ) or []
    return rows


def telegram_webhook_state(token: str) -> dict:
    if not token:
        return {"configured": False}
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getWebhookInfo",
            timeout=10,
        ) as response:
            payload = json.loads(response.read().decode()) or {}
        result = payload.get("result") or {}
        return {
            "configured": True,
            "url": result.get("url") or "",
            "pending_update_count": result.get("pending_update_count", 0),
            "has_webhook": bool(result.get("url")),
        }
    except Exception as exc:
        return {"configured": True, "error": str(exc)}


def recent_telegram_409_errors(limit: int = 200) -> int:
    log_path = Path(ROOT) / "telegram-integration.log"
    if not log_path.exists():
        return 0
    try:
        lines = log_path.read_text(errors="replace").splitlines()[-limit:]
    except Exception:
        return 0
    return sum(1 for line in lines if "error_code\":409" in line or "409" in line and "getUpdates failed" in line)


def script_processes(names: list[str]) -> list[str]:
    try:
        proc = subprocess.run(
            ["ps", "ax", "-o", "pid=", "-o", "command="],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    matches: list[str] = []
    for line in proc.stdout.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if "backend_health_report.py" in normalized:
            continue
        if any(name in normalized for name in names):
            if any(name.endswith(".py") for name in names) and ("python" not in normalized.lower()):
                continue
            matches.append(normalized)
    return matches


def main() -> int:
    telegram_processes = script_processes(["telegram_bot.py", "hermes_status_bot.py", "hermes_claude_bot.py"])
    scheduler_processes = script_processes(["operations_center/scheduler.py"])
    orchestrator_processes = script_processes(["services/nexus-orchestrator/src/index.js"])
    ops = get_ops_config()
    reports = get_reports_config()
    chat = get_chat_config()
    inbound_token = ops.token.strip()
    nexus_one_token = (os.getenv("NEXUS_ONE_BOT_TOKEN") or "").strip()
    inbound_poller_count = len(telegram_processes)

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
        "telegram_inbound": {
            "canonical_consumer": "telegram_bot.py",
            "ops_bot_configured": bool(ops.token and ops.chat_id),
            "reports_bot_configured": bool(reports.token and reports.chat_id),
            "hermes_chat_enabled": hermes_chat_enabled(),
            "shared_token_detected": shared_token_detected(),
            "inbound_token_source": ops.token_source,
            "canonical_process_count": len([line for line in telegram_processes if "telegram_bot.py" in line]),
            "inbound_poller_count": inbound_poller_count,
            "recent_telegram_409_errors": recent_telegram_409_errors(),
            "webhook_takeover_enabled": os.getenv("TELEGRAM_DELETE_WEBHOOK_ON_START", "false"),
            "canonical_webhook_state": telegram_webhook_state(inbound_token),
            "nexus_one_webhook_state": telegram_webhook_state(nexus_one_token),
            "ops_chat_source": ops.chat_source,
            "reports_token_source": reports.token_source,
            "chat_token_source": chat.token_source,
        },
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
