#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.telegram_role_config import (
    get_chat_config,
    get_ops_config,
    get_reports_config,
    hermes_chat_enabled,
    shared_token_detected,
    validate_chat_bot,
    validate_ops_polling,
    validate_reports_sender,
)
from lib.env_loader import load_nexus_env

load_nexus_env()
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
        if "check_telegram_bots.py" in normalized:
            continue
        if any(name in normalized for name in names):
            if any(name.endswith(".py") for name in names) and ("python" not in normalized.lower()):
                continue
            matches.append(normalized)
    return matches


def main() -> int:
    ops = get_ops_config()
    reports = get_reports_config()
    chat = get_chat_config()

    ok_ops, ops_errors = validate_ops_polling()
    ok_reports, reports_errors = validate_reports_sender()
    ok_chat, chat_messages = validate_chat_bot()

    pollers = script_processes(["telegram_bot.py", "hermes_status_bot.py", "hermes_claude_bot.py"])
    inbound_pollers = [line for line in pollers if any(name in line for name in ["telegram_bot.py", "hermes_status_bot.py", "hermes_claude_bot.py"])]
    hermes_chat_running = any("hermes_claude_bot.py" in line for line in pollers)
    errors = ops_errors + reports_errors + ([] if ok_chat else chat_messages)
    if len(inbound_pollers) != 1:
        errors.append(f"Expected exactly one inbound poller, found {len(inbound_pollers)}")
    if hermes_chat_running and not hermes_chat_enabled():
        errors.append("hermes_claude_bot.py is running even though ENABLE_HERMES_CHAT_BOT=false")

    report = {
        "ops_bot_configured": bool(ops.token and ops.chat_id),
        "reports_bot_configured": bool(reports.token and reports.chat_id),
        "hermes_chat_enabled": hermes_chat_enabled(),
        "shared_token_detected": shared_token_detected(),
        "ops_token_source": ops.token_source,
        "reports_token_source": reports.token_source,
        "chat_token_source": chat.token_source,
        "inbound_poller_count": len(inbound_pollers),
        "inbound_pollers": inbound_pollers,
        "hermes_chat_running": hermes_chat_running,
        "ops_validation_ok": ok_ops,
        "reports_validation_ok": ok_reports,
        "chat_validation_ok": ok_chat,
        "errors": errors,
        "notes": chat_messages if ok_chat else [],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
