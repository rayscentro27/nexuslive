#!/usr/bin/env python3
"""Validate Telegram outbound policy and wrapper discipline."""

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_gate import telegram_policy_allows_send

PASS = "✅ PASS"
FAIL = "❌ FAIL"

tests_run = 0
tests_passed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global tests_run, tests_passed
    tests_run += 1
    if condition:
        tests_passed += 1
        print(f"  {PASS}: {label}")
    else:
        print(f"  {FAIL}: {label}" + (f" - {detail}" if detail else ""))


print("\n[1] Policy deny cases")
deny_cases = [
    "scheduled_summary",
    "weekly_summary",
    "daily_summary",
    "background_report",
    "opportunity_brief",
    "research_brief",
    "trading_alert",
    "youtube_summary",
    "ingestion_summary",
    "automatic_status",
    "worker_summary",
    "model_error_report",
    "full_report",
]
for event_type in deny_cases:
    allowed, reason = telegram_policy_allows_send(event_type=event_type, source="scheduler")
    check(f"deny {event_type}", (not allowed) and reason == "scheduled_or_background_summary", reason)


print("\n[2] Policy allow cases")
allow_cases = [
    ("direct_chat_reply", {"source": "direct", "user_requested": True}),
    ("command_reply", {"source": "direct", "user_requested": True, "is_command": True}),
    ("approval_request", {"source": "direct", "user_requested": True, "is_approval": True}),
    ("approval_result", {"source": "direct", "user_requested": True, "is_approval": True}),
    ("user_requested_completion_notice", {"source": "direct", "user_requested": True, "is_completion": True}),
    ("user_requested_email_report_confirmation", {"source": "direct", "user_requested": True}),
]
for event_type, flags in allow_cases:
    allowed, reason = telegram_policy_allows_send(event_type=event_type, **flags)
    check(f"allow {event_type}", allowed, reason)


print("\n[3] Static wrapper guard")
allowed_sendmessage_files = {
    ROOT / "lib" / "hermes_gate.py",
}

try:
    proc = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    all_py_files = [ROOT / p for p in proc.stdout.splitlines() if p.strip()]
except Exception:
    all_py_files = list(ROOT.rglob("*.py"))
violations = []
for path in all_py_files:
    rel = str(path.relative_to(ROOT))
    if rel.startswith(".venv/") or rel.startswith("venv/"):
        continue
    if rel.startswith("scripts/test_") or rel.startswith("tests/"):
        continue
    text = path.read_text(encoding="utf-8")
    has_bypass = (
        "sendMessage" in text
        or "bot.send_message(" in text
        or "context.bot.send_message(" in text
        or "telegram.Bot(" in text
    )
    if has_bypass and path not in allowed_sendmessage_files:
        violations.append(rel)

check("all non-test Telegram sends go through hermes_gate", not violations, ", ".join(sorted(violations)[:8]))


print(f"\n{'=' * 52}")
print(f"  Telegram policy: {tests_passed}/{tests_run} tests passed")
if tests_passed == tests_run:
    print("  All tests passed.")
else:
    print(f"  {tests_run - tests_passed} test(s) FAILED - see above.")
print(f"{'=' * 52}\n")

sys.exit(0 if tests_passed == tests_run else 1)
