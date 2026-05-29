"""
test_common_language_responses.py
Verifies Hermes uses plain language by default, not raw logs.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_common_language_responses ===")

from lib.hermes_internal_first import try_internal_first

# Patterns that indicate raw/technical output (bad by default)
BAD_PATTERNS = [
    "Command timed out",
    "Try again in a moment",
    "No conversational LLM is available right now",
    "[verified_file]",
    "source_intake_registry JSONL contains",
    "monetization_score=",
    "risk_score=",
    "Action queued to",
    "Provider unavailable. Evidence-only fallback activated.",
    "Traceback",
    "KeyError:",
    "TypeError:",
]

PLAIN_LANGUAGE_COMMANDS = [
    "what are our goals",
    "what scouts are available",
    "what tools do you have",
    "show action queue",
    "show decision log",
    "what trading strategy do you recommend",
    "morning hermes",
    "what should I work on today",
    "what is nexus",
]

for cmd in PLAIN_LANGUAGE_COMMANDS:
    result = try_internal_first(cmd)
    if result is None:
        PASS += 1; print(f"  ✅ No internal reply for '{cmd[:40]}' (falls to LLM — acceptable)")
        continue
    for bad in BAD_PATTERNS:
        check(f"no bad pattern '{bad[:30]}' in '{cmd[:30]}'",
              bad not in result.text)
    check(f"reply for '{cmd[:40]}' is non-empty", len(result.text.strip()) > 15)

# Goals should be explained in plain English
result_goals = try_internal_first("what are our goals")
if result_goals:
    check("goals reply has no raw JSON braces as first char",
          not result_goals.text.strip().startswith("{"))
    check("goals reply reads naturally", len(result_goals.text.split()) >= 10)

# Action queue should use plain English
result_aq = try_internal_first("show action queue")
if result_aq:
    check("action queue reply no raw JSON dump", result_aq.text.count("{") < 5)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
