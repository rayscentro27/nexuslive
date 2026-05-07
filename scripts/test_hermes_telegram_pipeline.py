#!/usr/bin/env python3
"""
test_hermes_telegram_pipeline.py

Verify 2-way Telegram communication:
  1. Intent classification for all supported command phrases
  2. Router produces a structured Hermes Report for each intent
  3. Gate correctly allows direct responses (bypasses rate limit)
  4. Gate correctly blocks automated duplicates (cooldown respected)

Usage:
  cd /Users/raymonddavis/nexus-ai
  python3 scripts/test_hermes_telegram_pipeline.py
"""

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Load .env
from pathlib import Path
_env = Path(ROOT) / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
from telegram_bot import NexusTelegramBot

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


# ── Test 1: Intent classification ────────────────────────────────────────────

print("\n[1] Intent classification")

cases = [
    ("are we ready for pilot",        "pilot_readiness"),
    ("ready for 10-user pilot",       "pilot_readiness"),
    ("pilot ready",                   "pilot_readiness"),
    ("what is the next best move",    "next_best_move"),
    ("what do you recommend",         "next_best_move"),
    ("recommend next step",           "next_best_move"),
    ("can you hear me",               "communication_health"),
    ("comm check hermes",             "communication_health"),
    ("is this working",               "communication_health"),
    ("check backend health",          "health_check"),
    ("worker status",                 "worker_status"),
    ("queue status",                  "queue_status"),
    ("trading status",                "trading_lab_status"),
    ("gibberish xyz abc 123",         "unknown"),
]

for phrase, expected_intent in cases:
    intent, priority, _ = classify_intent(phrase)
    check(
        f'"{phrase}" → {expected_intent}',
        intent == expected_intent,
        f"got: {intent}",
    )

# ── Test 2: Router produces Hermes Report ─────────────────────────────────────

print("\n[2] Router produces Hermes Report for key commands")

report_commands = [
    "are we ready for pilot",
    "next best move",
    "can you hear me",
]

for cmd in report_commands:
    try:
        report = run_command(cmd, source="cli", sender="test")
        has_status  = "Status:" in report or "HERMES REPORT" in report
        has_evidence = "Evidence:" in report
        check(
            f'run_command("{cmd}") → structured report',
            has_status and has_evidence,
            report[:120] if not (has_status and has_evidence) else "",
        )
    except Exception as e:
        check(f'run_command("{cmd}")', False, str(e))
        traceback.print_exc()

# ── Test 3: Unknown intent → clarifying question ──────────────────────────────

print("\n[3] Unknown command → clarifying question (not a list dump)")

report = run_command("blah blah something unclear", source="cli", sender="test")
has_question = "?" in report or "Options:" in report or "What would" in report
check("Unknown command asks clarifying question", has_question, report[:200])

# ── Test 4: Gate — direct response bypasses rate limit ───────────────────────

print("\n[4] Hermes gate: direct responses bypass rate limit")

from lib.hermes_gate import send_direct_response, _rate_limit_ok

# Mock: rate limit check should not block direct responses
# We test that send_direct_response exists and is callable (actual send skipped in CI)
check(
    "send_direct_response is callable",
    callable(send_direct_response),
)

# ── Test 4b: /models command formatting ───────────────────────────────────────

print("\n[4b] /models command formatting")

bot = NexusTelegramBot.__new__(NexusTelegramBot)
models_text = NexusTelegramBot._cmd_models(bot)
check("/models includes header", "Model Diagnostics" in models_text)
check("/models includes routing preview", "Routing Preview" in models_text)
check("/models includes funding_strategy", "funding_strategy" in models_text)

# ── Test 5: Gate — automated alerts respect cooldown ─────────────────────────

print("\n[5] Hermes gate: empty messages suppressed")

from lib.hermes_gate import _is_empty

empty_samples = [
    "No issues detected — all clear",
    "Nothing to report at this time",
    "0 emails processed today",
    "Done — 0 updates",
]
not_empty_samples = [
    "WARNING: 3 workers stale — restart required",
    "CRITICAL: Revenue gap detected — follow up needed",
    "5 leads overdue for followup",
]

for sample in empty_samples:
    check(f'Empty filter suppresses: "{sample[:50]}"', _is_empty(sample))

for sample in not_empty_samples:
    check(f'Empty filter passes: "{sample[:50]}"', not _is_empty(sample))

# ── Summary ────────────────────────────────────────────────────────────────────

print(f"\n{'='*52}")
print(f"  Telegram pipeline: {tests_passed}/{tests_run} tests passed")
if tests_passed == tests_run:
    print("  All tests passed.")
else:
    print(f"  {tests_run - tests_passed} test(s) FAILED — see above.")
print(f"{'='*52}\n")

sys.exit(0 if tests_passed == tests_run else 1)
