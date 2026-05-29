"""
test_no_raw_evidence_dump_by_default.py
Verifies that evidence-only responses are cleanly formatted,
not raw file dumps with [verified_file] headers.
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

print("=== test_no_raw_evidence_dump_by_default ===")

# Force evidence_only mode
os.environ["HERMES_ALLOW_HERMES_GATEWAY"] = "false"
os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:19992"  # unreachable
os.environ.pop("OPENAI_API_KEY", None)

import lib.hermes_provider_policy as pp
pp._policy = None
pp.get_policy(refresh=True)

from lib.hermes_reasoning_layer import reason

QUERIES = [
    "what should I work on today",
    "what trading strategy do you recommend",
    "good morning",
    "what is nexus",
]

BAD_PATTERNS = [
    "No conversational LLM is available right now.",
    "Command timed out",
    "Try again in a moment",
    "[verified_file]",
    "Here is what I have verified:\n",
]

for q in QUERIES:
    result = reason(q, evidence_text="", ops_context="")
    check(f"result for '{q[:40]}' is not None", result is not None)
    if result:
        check(f"result is evidence_only: '{q[:40]}'", result.is_evidence_only or result.provider_used == "evidence_only")
        for bad in BAD_PATTERNS:
            check(f"no bad pattern '{bad[:40]}' in '{q[:30]}'",
                  bad not in result.reply)
        check(f"reply is meaningful (>20 chars): '{q[:40]}'", len(result.reply) > 20)

# Verify the formatter is used (clean format check)
result_today = reason("what should I work on today", evidence_text="", ops_context="")
if result_today:
    check("today reply starts with clean text (not 'No...')",
          not result_today.reply.startswith("No conversational"))

# cleanup
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_ALLOW_OPENROUTER_FALLBACK", None)
os.environ.pop("OLLAMA_HOST", None)
pp._policy = None

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
