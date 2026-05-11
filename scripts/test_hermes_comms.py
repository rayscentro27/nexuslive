#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.prelaunch_utils import count_by, default_test_mode, pgrep_lines, probe_port, rest_select
from lib.telegram_role_config import get_ops_config, get_reports_config, hermes_chat_enabled, shared_token_detected


def str_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def dashboard_probe() -> dict:
    url = "http://127.0.0.1:4000/api/prelaunch/audit"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode())
            return {
                "ok": response.status == 200,
                "status": response.status,
                "superadmin_ready": bool((payload.get("superadmin") or {}).get("auth_exists")),
                "scheduler_running": bool((payload.get("runtime") or {}).get("scheduler_running")),
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def duplicate_detection() -> dict:
    telegram_processes = pgrep_lines("telegram_bot.py|hermes_status_bot.py|hermes_claude_bot.py")
    event_mix = count_by("system_events", "event_type")
    ignored_ceo = len(
        rest_select(
            "system_events?select=id,status,event_type&event_type=eq.ceo_routed&status=eq.ignored&limit=20"
        ) or []
    )
    return {
        "telegram_process_count": len(telegram_processes),
        "telegram_processes": telegram_processes,
        "canonical_consumer": "telegram_bot.py",
        "ops_token_source": get_ops_config().token_source,
        "reports_token_source": get_reports_config().token_source,
        "hermes_chat_enabled": hermes_chat_enabled(),
        "shared_token_detected": shared_token_detected(),
        "ignored_ceo_routed_events": ignored_ceo,
        "event_mix": event_mix,
        "status": "ok" if len(telegram_processes) <= 1 and ignored_ceo <= 1 else "attention",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", nargs="?", const="true", default="true")
    args = parser.parse_args()
    dry_run = str_bool(args.dry_run, True)

    report = {
        "dry_run": dry_run,
        "test_mode_default": default_test_mode(),
        "dashboard_command_result": dashboard_probe(),
        "workflow_output_id": None,
        "telegram_enabled": os.getenv("SCHEDULER_TELEGRAM_ENABLED", "true"),
        "email_enabled": os.getenv("SCHEDULER_EMAIL_ENABLED", "false"),
        "control_center_up": probe_port("127.0.0.1", 4000),
        "ceo_route_worker_running": bool(pgrep_lines("lib/ceo_routed_worker.py")),
        "ceo_routing_loop_running": bool(pgrep_lines("lib/ceo_routing_loop.py")),
        "duplicate_detection_result": duplicate_detection(),
        "notes": [
            "Dry-run mode does not create a live dashboard command event.",
            "Telegram and email remain opt-in and are only reported here.",
        ],
    }

    if not dry_run:
        body = json.dumps({"message": "Dry-run disabled Hermes comms probe", "channel": "prelaunch_test"}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:4000/api/route-job",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode())
            report["dashboard_command_result"] = payload
            draft_rows = rest_select(
                "workflow_outputs?select=id,workflow_type,status&workflow_type=eq.ceo_routed_draft&order=created_at.desc&limit=1"
            ) or []
            report["workflow_output_id"] = draft_rows[0]["id"] if draft_rows else None
        except urllib.error.HTTPError as exc:
            report["dashboard_command_result"] = {"ok": False, "error": exc.read().decode()}
        except Exception as exc:
            report["dashboard_command_result"] = {"ok": False, "error": str(exc)}

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
