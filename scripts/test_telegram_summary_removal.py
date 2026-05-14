#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.telegram_notification_policy import should_send_telegram_notification


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    os.environ["TELEGRAM_OPERATIONAL_NOTIFICATIONS_ENABLED"] = "false"
    os.environ["TELEGRAM_CRITICAL_ALERTS_ENABLED"] = "true"

    allowed, _ = should_send_telegram_notification("conversational_reply", conversational=True)
    ok &= check("good morning conversational reply allowed", allowed)

    allowed, _ = should_send_telegram_notification("explicit_operator_requested_digest", user_requested=True)
    ok &= check("explicit digest request allowed", allowed)

    denied, reason = should_send_telegram_notification("research_summary")
    ok &= check("research worker auto summary denied", (not denied) and reason == "blocked_event_type")

    denied, reason = should_send_telegram_notification("ingestion_summary")
    ok &= check("ingestion auto summary denied", (not denied) and reason == "blocked_event_type")

    denied, reason = should_send_telegram_notification("scheduler_summary")
    ok &= check("scheduler summary denied", (not denied) and reason == "blocked_event_type")

    denied, reason = should_send_telegram_notification("ticket_summary")
    ok &= check("open tickets summary denied", (not denied) and reason == "blocked_event_type")

    denied, reason = should_send_telegram_notification("")
    ok &= check("missing event type denied", (not denied) and reason == "missing_event_type")

    denied, _ = should_send_telegram_notification("worker_summary")
    ok &= check("legacy worker summary path denied", not denied)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
