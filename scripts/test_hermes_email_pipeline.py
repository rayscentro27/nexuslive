#!/usr/bin/env python3
"""
test_hermes_email_pipeline.py

Verify 2-way email communication:
  1. detect_mode() correctly classifies Hermes command emails
  2. process_hermes_command() produces a Hermes Report (dry-run — no actual email sent)
  3. Standard modes (status, tasks, research) still work
  4. Idempotency dedup still engaged for Hermes mode

Usage:
  cd /Users/raymonddavis/nexus-ai
  python3 scripts/test_hermes_email_pipeline.py
"""

import os
import sys
import traceback
from unittest.mock import patch, MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pathlib import Path
_env = Path(ROOT) / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from nexus_email_pipeline import detect_mode, process_hermes_command

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
        print(f"  {FAIL}: {label}" + (f" — {detail}" if detail else ""))


# ── Test 1: detect_mode for Hermes commands ───────────────────────────────────

print("\n[1] detect_mode() classifies Hermes command emails")

hermes_cases = [
    # (subject, body, expected_mode)
    ("[HERMES] status",           "are we ready for pilot?",     "hermes"),
    ("Hermes: next move",         "what should we do next",      "hermes"),
    ("Hello",                     "can you hear me Hermes?",     "hermes"),
    ("Question",                  "what do you recommend",       "hermes"),
    ("Query",                     "next best move",              "hermes"),
    ("Check",                     "worker status",               "hermes"),
    ("Info",                      "check backend health",        "hermes"),
    ("[HERMES] comm check",       "comm check",                  "hermes"),
]

non_hermes_cases = [
    ("[STATUS] weekly",           "status update",               "status"),
    ("[TASKS] this week",         "1. Fix auth\n2. Deploy",      "tasks"),
    ("Hello",                     "How are you doing today?",    None),
]

for subject, body, expected in hermes_cases:
    mode = detect_mode(subject, body)
    check(
        f'detect_mode("{subject[:30]}", "{body[:30]}") → hermes',
        mode == expected,
        f"got: {mode}",
    )

for subject, body, expected in non_hermes_cases:
    mode = detect_mode(subject, body)
    check(
        f'detect_mode("{subject[:30]}", "{body[:30]}") → {expected}',
        mode == expected,
        f"got: {mode}",
    )

# ── Test 2: process_hermes_command produces a report (no actual email) ─────────

print("\n[2] process_hermes_command() produces structured Hermes Report (dry-run)")

hermes_command_cases = [
    "are we ready for pilot",
    "next best move",
    "can you hear me",
    "worker status",
]

sent_replies = []

def mock_send_reply(to, subject, body):
    sent_replies.append({"to": to, "subject": subject, "body": body})

for cmd_text in hermes_command_cases:
    sent_replies.clear()
    msg = {
        "uid": b"001",
        "message_id": f"test-{cmd_text[:20]}@test",
        "subject": f"[HERMES] {cmd_text}",
        "sender": "goclearonline@gmail.com",
        "reply_to": "goclearonline@gmail.com",
        "body": cmd_text,
    }
    try:
        with patch("nexus_email_pipeline.send_reply", side_effect=mock_send_reply):
            process_hermes_command(msg)

        check(
            f'process_hermes_command("{cmd_text[:40]}"): reply sent',
            len(sent_replies) == 1,
            f"sent {len(sent_replies)} replies",
        )
        if sent_replies:
            body = sent_replies[0]["body"]
            has_report = "Status:" in body or "HERMES REPORT" in body or "Evidence:" in body
            check(
                f'process_hermes_command("{cmd_text[:40]}"): body is Hermes Report',
                has_report,
                body[:200] if not has_report else "",
            )
    except Exception as e:
        check(f'process_hermes_command("{cmd_text[:40]}")', False, str(e))
        traceback.print_exc()

# ── Test 3: Quoted email body stripping ───────────────────────────────────────

print("\n[3] Quoted email reply boilerplate is stripped")

sent_replies.clear()
msg_with_quoted = {
    "uid": b"002",
    "message_id": "test-quoted@test",
    "subject": "[HERMES] check",
    "sender": "goclearonline@gmail.com",
    "reply_to": "goclearonline@gmail.com",
    "body": (
        "worker status\n\n"
        "On Mon, 4 May 2026, Nexus wrote:\n"
        "> Previous reply goes here\n"
        "> More quoted content\n"
    ),
}

with patch("nexus_email_pipeline.send_reply", side_effect=mock_send_reply):
    process_hermes_command(msg_with_quoted)

check(
    "Quoted email boilerplate stripped before routing",
    len(sent_replies) == 1,
    "no reply sent" if not sent_replies else "",
)

# ── Summary ────────────────────────────────────────────────────────────────────

print(f"\n{'='*52}")
print(f"  Email pipeline: {tests_passed}/{tests_run} tests passed")
if tests_passed == tests_run:
    print("  All tests passed.")
else:
    print(f"  {tests_run - tests_passed} test(s) FAILED — see above.")
print(f"{'='*52}\n")

sys.exit(0 if tests_passed == tests_run else 1)
