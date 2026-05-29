"""
test_no_demo_status_responses.py
Verifies greeting responses no longer contain stale hardcoded execution priorities.
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

print("=== test_no_demo_status_responses ===")

from lib.hermes_executive_memory import load_memory

mem = load_memory(force_refresh=True)
priorities = mem.get("execution_priorities", [])

STALE_STRINGS = [
    "Get content engine running",
    "Beehiiv and YouTube Studio",
    "Remediate 7 false completions",
    "Route daily content through OpenRouter",
]

# 1. Stale priorities are cleared from default memory
check("execution_priorities is empty list by default", priorities == [])

for s in STALE_STRINGS:
    check(f"stale string not in priorities: {s[:40]}", not any(s.lower() in str(p).lower() for p in priorities))

# 2. Greeting context builder does not include stale strings
from lib.hermes_internal_first import _build_operational_context_brief
ctx = _build_operational_context_brief()
for s in STALE_STRINGS:
    check(f"stale string not in greeting context: {s[:40]}", s.lower() not in ctx.lower())

# 3. Operational philosophy is still present (safety model intact)
philosophy = mem.get("operational_philosophy", [])
check("operational_philosophy is still populated", len(philosophy) > 0)
check("DRY_RUN rule still in philosophy", any("DRY_RUN" in str(p) for p in philosophy))

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
