"""
test_nexus_monetization_audit_no_evidence_dump.py
Verifies 'nexus monetization audit' does NOT return the generic evidence dump.
Tests both the run_command path and the _run_business_opportunities handler.
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

print("=== test_nexus_monetization_audit_no_evidence_dump ===\n")

from hermes_command_router.router import run_command, _run_business_opportunities
from hermes_command_router.intake import classify_intent

FORBIDDEN_IN_AUDIT = [
    "I can answer from verified artifacts",
    "Monetization evidence:",
    "Evidence used:",
    "[artifact_inventory]",
    "[revenue_plan]",
    "docs/reports/handoffs",
    "docs/reports/intake",
    "docs/reports/core",
]

# ── classify_intent routes audit phrase ─────────────────────────────────────
print("-- Intent classification for audit phrases --")
for phrase in [
    "nexus monetization audit",
    "run nexus monetization audit",
    "show monetization audit",
    "monetization audit",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → business_opportunities", intent == "business_opportunities")

# ── run_command 'nexus monetization audit' ──────────────────────────────────
print("\n-- run_command: nexus monetization audit --")
result = run_command("nexus monetization audit")
check("result is non-empty", bool(result))
for marker in FORBIDDEN_IN_AUDIT:
    check(f"no forbidden: '{marker[:40]}'", marker not in result)
check("result has AUDIT or PLAN or asset info",
      any(h in result for h in ("AUDIT", "PLAN", "asset", "Lead", "Newsletter", "Video", "score")))

# ── run_command 'show monetization audit' ────────────────────────────────────
print("\n-- run_command: show monetization audit --")
result2 = run_command("show monetization audit")
check("result is non-empty", bool(result2))
for marker in FORBIDDEN_IN_AUDIT:
    check(f"no forbidden: '{marker[:40]}'", marker not in result2)

# ── _run_business_opportunities does not produce stale exec memory output ────
print("\n-- _run_business_opportunities handler --")
status, evidence, rec = _run_business_opportunities()
full = "\n".join(evidence) + "\n" + rec
check("status is not None", status is not None)
check("no 'I can answer from verified artifacts'", "I can answer from verified artifacts" not in full)
check("no '[artifact_inventory]'", "[artifact_inventory]" not in full)
check("recommendation is non-empty", bool(rec))
check("no stale OFFLINE marker", "OFFLINE" not in full)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
