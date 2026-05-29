"""
test_hermes_memory_sources.py
Verifies all internal handlers cite a real source (not "hermes_reasoning_layer").
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

print("=== test_hermes_memory_sources ===")

from lib.hermes_internal_first import try_internal_first

INTERNAL_QUERIES = [
    ("where do you get your information", "information_sources"),
    ("what is nexus", "nexus_project"),
    ("30 day goals", "goals_30_day"),
    ("what did claude code work on", "claude_code_work"),
    ("youtube status", "youtube_status"),
    ("what are the priorities", "execution_priorities"),
    ("show provider status", "ai_providers"),
]

for query, expected_topic in INTERNAL_QUERIES:
    result = try_internal_first(query)
    check(f"returns result for: {query[:45]}", result is not None)
    if result:
        check(f"correct topic for: {query[:45]}", result.matched_topic == expected_topic)
        check(f"source is not LLM for: {query[:40]}", result.source != "hermes_reasoning_layer")
        check(f"reply is non-empty for: {query[:40]}", len(result.text.strip()) > 10)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
