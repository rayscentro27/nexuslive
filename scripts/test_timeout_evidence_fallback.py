"""
test_timeout_evidence_fallback.py
Verifies that questions answered by internal handlers never reach the LLM,
so a provider timeout cannot prevent a memory-based answer.
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

print("=== test_timeout_evidence_fallback ===")

# Force all providers offline
os.environ["HERMES_GATEWAY_URL"] = "http://127.0.0.1:19999"
os.environ["HERMES_GATEWAY_KEY"] = "fake_timeout_test"
os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"

import lib.hermes_provider_policy as pp
pp.get_policy(refresh=True)

from lib.hermes_internal_first import try_internal_first

# These questions MUST return internal answers regardless of provider status
MEMORY_QUESTIONS = [
    "what is nexus",
    "30 day goals",
    "where do you get your information",
    "what did claude code work on",
    "youtube status",
    "what are the priorities",
    "what ai providers are available",
]

for q in MEMORY_QUESTIONS:
    result = try_internal_first(q)
    check(f"internal reply exists despite no providers: {q[:45]}", result is not None)
    if result:
        check(f"reply is non-empty: {q[:45]}", len(result.text.strip()) > 5)

# cleanup
del os.environ["HERMES_GATEWAY_URL"]
del os.environ["HERMES_GATEWAY_KEY"]
del os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"]

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
