"""
test_information_sources_response.py
Verifies "where do you get your information" returns a real source list, not LLM invention.
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

print("=== test_information_sources_response ===")

from lib.hermes_internal_first import try_internal_first

QUERIES = [
    "where do you get your information",
    "what are your sources",
    "where does this data come from",
    "information sources",
    "how do you know that",
]

for q in QUERIES:
    result = try_internal_first(q)
    check(f"has internal reply for: {q[:45]}", result is not None)
    if result:
        check(f"reply mentions docs/reports: {q[:35]}", "docs/reports" in result.text or "artifacts" in result.text)
        check(f"reply mentions evidence-only: {q[:35]}", "evidence" in result.text.lower())
        check(f"source is not LLM: {q[:35]}", result.source != "hermes_reasoning_layer")
        check(f"topic is information_sources: {q[:35]}", result.matched_topic == "information_sources")

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
