"""
test_cfo_conversation_plain_language.py
Tests: Ray concern message returns CFO-style plain-language response with required sections.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_cfo_conversation_plain_language ===\n")

from lib.hermes_cfo_conversation_layer import (
    build_cfo_context, build_cfo_response, format_cfo_response,
)

# ── Ray's actual messages from the Phase 7 directive ─────────────────────────
TEST_MESSAGES = [
    "I am worried Hermes is becoming a command bot and not a CFO",
    "What should we do about that?",
    "I don't know what ChatGPT has that Hermes doesn't, but I need that logic",
    "Right now it feels more like a master/dog relationship than a CEO/CFO relationship",
]

print("-- CFO response format for Ray's messages --")
for msg in TEST_MESSAGES:
    ctx = build_cfo_context(msg)
    resp = build_cfo_response(msg, ctx)
    formatted = format_cfo_response(resp)

    check(f"'{msg[:50]}...' → CFO response starts with RAY",
          formatted.startswith("RAY") or formatted.startswith("I DON'T"))
    check(f"'{msg[:50]}...' → has approval boundary",
          "Approval boundary" in formatted or "approval" in formatted.lower())
    check(f"'{msg[:50]}...' → not empty", len(formatted.strip()) > 50)

# ── CFO response structure for hermes_behavior_feedback ──────────────────────
print("\n-- hermes_behavior_feedback response structure --")
msg = "I am worried Hermes is becoming a command bot and not a CFO"
ctx = build_cfo_context(msg)
resp = build_cfo_response(msg, ctx)
formatted = format_cfo_response(resp)
formatted_lower = formatted.lower()

check("response has 'real issue' section",
      "real issue" in formatted_lower or "concern" in formatted_lower)
check("response has 'what i know' section",
      "what i know" in formatted_lower or "currently" in formatted_lower)
check("response has options",
      "option" in formatted_lower or "1." in formatted)
check("response has recommendation",
      "recommendation" in formatted_lower or "recommend" in formatted_lower)
check("response has next steps",
      "what i can do" in formatted_lower or "next" in formatted_lower)
check("response mentions learning loop",
      "learning loop" in formatted_lower or "record this lesson" in formatted_lower)

# ── Monetization strategy response ───────────────────────────────────────────
print("\n-- monetization strategy response --")
mon_msg = "How do we make $1000 a week from affiliate revenue?"
mon_ctx = build_cfo_context(mon_msg)
mon_resp = build_cfo_response(mon_msg, mon_ctx)
mon_fmt = format_cfo_response(mon_resp)
mon_lower = mon_fmt.lower()

check("monetization response is non-empty", len(mon_fmt.strip()) > 50)
check("monetization response has recommendation",
      "recommendation" in mon_lower or "recommend" in mon_lower)
check("monetization response has approval boundary",
      "approval boundary" in mon_lower or "approval" in mon_lower)

# ── Implementation prompt response ───────────────────────────────────────────
print("\n-- implementation prompt response --")
impl_msg = "Give me a prompt for Claude to fix this"
impl_ctx = build_cfo_context(impl_msg)
impl_resp = build_cfo_response(impl_msg, impl_ctx)
impl_fmt = format_cfo_response(impl_resp)
impl_lower = impl_fmt.lower()

check("implementation prompt starts with 'IMPLEMENTATION PROMPT'",
      impl_fmt.startswith("IMPLEMENTATION PROMPT"))
check("implementation prompt has goal",
      "goal:" in impl_lower)
check("implementation prompt has safety",
      "safety:" in impl_lower or "safety" in impl_lower)
check("implementation prompt has tests",
      "test" in impl_lower)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
