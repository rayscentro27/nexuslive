#!/usr/bin/env python3
"""
test_telegram_log_policy.py

Validates the Telegram outbound policy repair:
1. Forbidden research summary patterns blocked from Telegram
2. "What AI providers are available?" returns Nexus-internal answer
3. "What should I focus on today?" routes internal-first and is concise
4. NotebookLM queue query still works
5. Completion notices still pass policy
6. Email reports still pass policy
7. Safety flags unchanged
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

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


# ── [1] Forbidden content filter ────────────────────────────────────────────────

print("\n[1] Forbidden content patterns blocked at gate")
from lib.hermes_gate import _contains_forbidden_content, telegram_policy_allows_send

forbidden = [
    "🏛️ Nexus Research — Weekly Digest",
    "🏛️ Nexus Intelligence Brief",
    "🏛️ Nexus Research Run Complete",
    "Key Findings: 3 strategies extracted",
    "Sources: Bloomberg, Reuters",
    "Research artifacts saved to reports/",
    "nexus intelligence brief: attached",
]
safe = [
    "✅ Research report saved. I kept the full summary out of Telegram.",
    "Worker status: 3 running",
    "Funding readiness score: 72",
    "Approved. Task queued.",
    "Telegram routing repaired.",
]
for msg in forbidden:
    check(f'Blocked: "{msg[:55]}"', _contains_forbidden_content(msg))
for msg in safe:
    check(f'Allowed: "{msg[:55]}"', not _contains_forbidden_content(msg))


# ── [2] AI providers routes internal-first with Nexus-specific answer ───────────

print("\n[2] 'What AI providers are available?' → Nexus-internal answer")
from lib.hermes_internal_first import try_internal_first

r_providers = try_internal_first("What AI providers are available?")
check("routes to ai_providers topic", r_providers is not None and r_providers.matched_topic == "ai_providers")
check("reply mentions OpenRouter", r_providers is not None and "openrouter" in r_providers.text.lower())
check("reply mentions Claude Code", r_providers is not None and "claude" in r_providers.text.lower())
check("no generic public AI (DeepMind)", r_providers is None or "deepmind" not in r_providers.text.lower())
check("no generic public AI (Bard)", r_providers is None or "bard" not in r_providers.text.lower())
check("no generic public AI (AlphaFold)", r_providers is None or "alphafold" not in r_providers.text.lower())
check("no 'Direct answer:' prefix", r_providers is None or not r_providers.text.startswith("Direct answer:"))

r_claude = try_internal_first("Is Claude available?")
check("'Is Claude available?' → ai_providers", r_claude is not None and r_claude.matched_topic == "ai_providers")

r_openclaw = try_internal_first("Is OpenClaw available?")
check("'Is OpenClaw available?' → ai_providers", r_openclaw is not None and r_openclaw.matched_topic == "ai_providers")

r_fallback = try_internal_first("What fallback provider should I use?")
check("'What fallback provider?' → ai_providers", r_fallback is not None and r_fallback.matched_topic == "ai_providers")


# ── [3] "What should I focus on today?" routes internal-first ───────────────────

print("\n[3] 'What should I focus on today?' → internal-first (today topic)")
r_focus = try_internal_first("What should I focus on today?")
check("routes to today topic", r_focus is not None and r_focus.matched_topic == "today")
check("no 'Direct answer:' prefix", r_focus is None or not r_focus.text.startswith("Direct answer:"))
check("no 'Source:' label in text", r_focus is None or "source:" not in r_focus.text.lower())

r_focus2 = try_internal_first("What to focus on today?")
check("'What to focus on today?' → today", r_focus2 is not None and r_focus2.matched_topic == "today")

r_work = try_internal_first("What should I work on today?")
check("'What should I work on today?' → today", r_work is not None and r_work.matched_topic == "today")


# ── [4] NotebookLM queue query works ────────────────────────────────────────────

print("\n[4] NotebookLM queue query still works")
r_nlm = try_internal_first("What NotebookLM research is ready?")
check("routes to notebooklm topic", r_nlm is not None and r_nlm.matched_topic == "notebooklm")
check("no 'Direct answer:' prefix", r_nlm is None or not r_nlm.text.startswith("Direct answer:"))


# ── [5] Completion notices pass policy ──────────────────────────────────────────

print("\n[5] Completion notices pass gate policy")
allowed, reason = telegram_policy_allows_send(
    event_type="user_requested_completion_notice",
    source="direct",
    user_requested=True,
    is_completion=True,
)
check("completion notice allowed", allowed, reason)


# ── [6] Email report path allowed ───────────────────────────────────────────────

print("\n[6] Email report confirmation passes policy")
allowed_report, reason_report = telegram_policy_allows_send(
    event_type="user_requested_email_report_confirmation",
    source="direct",
    user_requested=True,
)
check("email report confirmation allowed", allowed_report, reason_report)


# ── [7] Safety flags unchanged ──────────────────────────────────────────────────

print("\n[7] Safety flags confirmed OFF")

def env_false(name: str) -> bool:
    val = (os.getenv(name, "false") or "false").strip().lower()
    return val not in {"1", "true", "yes", "on"}

# Load .env
from pathlib import Path
env_path = Path(ROOT) / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

check("TELEGRAM_AUTO_REPORTS_ENABLED=false", env_false("TELEGRAM_AUTO_REPORTS_ENABLED"))
check("TELEGRAM_FULL_REPORTS_ENABLED=false", env_false("TELEGRAM_FULL_REPORTS_ENABLED"))
check("SWARM_EXECUTION_ENABLED=false", env_false("SWARM_EXECUTION_ENABLED"))
check("HERMES_CLI_EXECUTION_ENABLED=false", env_false("HERMES_CLI_EXECUTION_ENABLED"))
check("TRADING_LIVE_EXECUTION_ENABLED=false", env_false("TRADING_LIVE_EXECUTION_ENABLED"))


# ── Summary ──────────────────────────────────────────────────────────────────────

print(f"\n{'=' * 52}")
print(f"  Telegram log policy: {tests_passed}/{tests_run} tests passed")
if tests_passed == tests_run:
    print("  All tests passed.")
else:
    print(f"  {tests_run - tests_passed} test(s) FAILED — see above.")
print(f"{'=' * 52}\n")

sys.exit(0 if tests_passed == tests_run else 1)
