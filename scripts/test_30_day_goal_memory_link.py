"""
test_30_day_goal_memory_link.py
Verifies "30 day goals" returns the revenue plan file, not invented content.
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

print("=== test_30_day_goal_memory_link ===")

from lib.hermes_internal_first import try_internal_first
from pathlib import Path

QUERIES = [
    "30 day goals",
    "30 day plan",
    "what is the 30 day plan",
    "monthly goals",
    "what are the 30 day goals",
    "revenue plan",
    "monthly revenue plan",
]

for q in QUERIES:
    result = try_internal_first(q)
    check(f"has internal reply for: {q}", result is not None)
    if result:
        check(f"topic is goals_30_day: {q}", result.matched_topic == "goals_30_day")
        check(f"not LLM source: {q}", "hermes_reasoning_layer" not in result.source)

# If plan file exists, verify it's loaded
plan_dir = Path(__file__).resolve().parent.parent / "docs" / "reports" / "monetization"
plan_files = sorted(plan_dir.glob("30_day_revenue_plan_*.md"), reverse=True) if plan_dir.exists() else []
check("plan file exists on disk", len(plan_files) > 0)
if plan_files:
    result = try_internal_first("what is the 30 day plan")
    check("reply contains revenue target or week", result is not None and (
        "week" in result.text.lower() or "$" in result.text or "target" in result.text.lower()
    ))
    check("source points to file", plan_files[0].name in result.source if result else False)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
