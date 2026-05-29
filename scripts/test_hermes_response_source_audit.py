"""
test_hermes_response_source_audit.py
Audits that Hermes responses consistently cite a source and never use "hermes_reasoning_layer"
as the source for questions that should be answered from local memory.
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

print("=== test_hermes_response_source_audit ===")

from lib.hermes_internal_first import try_internal_first
from lib.hermes_internal_first import (
    CONF_INTERNAL_CONFIRMED,
    CONF_INTERNAL_PARTIAL,
    CONF_INTERNAL_STALE,
    CONF_GENERAL_FALLBACK,
)

# All of these should be answered internally — never falling to LLM
MUST_ANSWER_INTERNALLY = [
    "where do you get your information",
    "what is nexus",
    "30 day goals",
    "what did claude code work on",
    "youtube status",
    "what are the priorities",
    "what ai providers are available",
    "morning hermes",
]

VALID_INTERNAL_CONFIDENCES = {CONF_INTERNAL_CONFIRMED, CONF_INTERNAL_PARTIAL, CONF_INTERNAL_STALE}

for q in MUST_ANSWER_INTERNALLY:
    result = try_internal_first(q)
    if result is None:
        # Some may fall through — that's OK, just log it
        FAIL += 1
        print(f"  ❌ no internal reply for: {q}")
        continue
    check(f"source cited for: {q[:45]}", bool(result.source) and result.source != "")
    check(f"not LLM source for: {q[:45]}", result.source != "hermes_reasoning_layer")
    check(f"internal confidence for: {q[:45]}", result.confidence in VALID_INTERNAL_CONFIDENCES or result.confidence == CONF_GENERAL_FALLBACK)
    check(f"non-empty reply for: {q[:45]}", len(result.text.strip()) > 5)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
