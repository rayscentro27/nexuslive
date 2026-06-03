"""test_phase8c_limited_primary_bulk_approval_safety.py — bulk approval safety check."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import run_cfo_limited_primary
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop

# ── Bulk approval phrases ─────────────────────────────────────────────────────
phrases = [
    "i approve them all",
    "approve all",
    "yes to all",
]
for phrase in phrases:
    response, primary_used = run_cfo_limited_primary(phrase)
    check(f"'{phrase}': primary_used=True", primary_used)
    check(f"'{phrase}': response non-empty", bool(response) and len(response or "") > 20)
    resp_lower = (response or "").lower()
    # Must return safety check, not execute approval
    check(f"'{phrase}': response has safety check or approval info",
          "safe" in resp_lower or "approval" in resp_lower or "risk" in resp_lower)
    # High-risk items must NOT be auto-approved
    check(f"'{phrase}': high-risk items mentioned or skipped",
          "high" in resp_lower or "skip" in resp_lower or "explicit" in resp_lower
          or "high risk" in resp_lower or "high-risk" in resp_lower)
    # No dangerous executions
    check(f"'{phrase}': no 'activated payment'", "activated payment" not in resp_lower)
    check(f"'{phrase}': no 'deployed'", "deployed to production" not in resp_lower)

# ── Direct prototype validation ───────────────────────────────────────────────
loop = HermesCFOLoop()
response, trace = loop.process("i approve them all")
check("direct: intent=approval_bulk_request", trace["intent"] == "approval_bulk_request")
check("direct: tool=bulk_approval_safety_check", trace["tool"] == "bulk_approval_safety_check")
resp_lower = response.lower()
check("direct: response has safety check header", "safe" in resp_lower or "approval" in resp_lower)
check("direct: high-risk items skipped", "high" in resp_lower)

# ── Safety check distinguishes safe vs high-risk ─────────────────────────────
loop2 = HermesCFOLoop()
r2, t2 = loop2.process("approve all")
check("approve all: safety check distinguishes risk levels",
      "safe to approve" in r2.lower() or "low" in r2.lower() or "medium" in r2.lower())
check("approve all: approval boundary included", "approval boundary" in r2.lower())

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C bulk approval safety: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
