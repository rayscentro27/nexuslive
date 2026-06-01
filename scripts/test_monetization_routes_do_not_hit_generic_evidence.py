"""
test_monetization_routes_do_not_hit_generic_evidence.py
Verifies that all monetization-intent phrases do NOT produce the old generic
evidence dump response.

Forbidden markers that must NOT appear in any monetization response:
- "I can answer from verified artifacts"
- "Monetization evidence:"
- "Evidence used:"
- "[artifact_inventory]"
- "[revenue_plan]"
- "docs/reports/handoffs"
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_monetization_routes_do_not_hit_generic_evidence ===\n")

from hermes_command_router.router import run_command

FORBIDDEN = [
    "I can answer from verified artifacts",
    "Monetization evidence:",
    "Evidence used:",
    "[artifact_inventory]",
    "[revenue_plan]",
    "docs/reports/handoffs",
]

MONETIZATION_PHRASES = [
    "how do we make money today",
    "how can we make money today",
    "how to make money today",
    "best money making opportunity",
    "nexus monetization audit",
    "run nexus monetization audit",
    "show monetization audit",
    "monetization plan",
    "monetization priorities",
    "revenue plan for today",
    "fastest money path",
    "what is our fastest money path",
    "what can make money this week",
    "best revenue move",
]

print("-- Checking no forbidden markers in monetization responses --")
for phrase in MONETIZATION_PHRASES:
    result = run_command(phrase)
    for marker in FORBIDDEN:
        check(f"'{phrase[:35]}' no '{marker[:30]}'", marker not in result)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
