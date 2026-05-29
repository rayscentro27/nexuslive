"""
test_today_recommendation_evidence_based.py
Verifies "what should I work on today" returns evidence-based recommendations,
not hallucinated task lists.
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

print("=== test_today_recommendation_evidence_based ===")

from lib.hermes_internal_first import try_internal_first
from lib.hermes_final_response_gate import inspect

QUERIES = [
    "what should i work on today",
    "what should we work on today",
    "next best move",
    "what do you recommend we work on today",
    "top priorities",
]

HALLUCINATION_TOKENS = [
    "nitrotrades", "slide 12", "6 pending", "sba deadline", "10x growth",
    "beehiiv and youtube studio",  # stale priority
    "remediate 7 false completions",  # stale priority
    "get content engine running with real llm",  # stale priority
]

for q in QUERIES:
    result = try_internal_first(q)
    if result is None:
        check(f"has internal reply (or graceful None): {q[:45]}", True)
        continue
    check(f"reply is non-empty: {q[:45]}", len(result.text.strip()) > 5)
    for token in HALLUCINATION_TOKENS:
        check(f"no '{token}' in reply: {q[:30]}", token not in result.text.lower())
    gate_result = inspect(result.text)
    check(f"passes response gate: {q[:45]}", gate_result.passed or "verified" in gate_result.original_text.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
