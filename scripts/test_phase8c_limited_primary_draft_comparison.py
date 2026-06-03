"""test_phase8c_limited_primary_draft_comparison.py — draft_comparison intent."""
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

# ── Draft comparison phrases ──────────────────────────────────────────────────
phrases = [
    "what changed in the draft",
    "what changed",
    "what's different",
]
for phrase in phrases:
    response, primary_used = run_cfo_limited_primary(phrase)
    check(f"'{phrase}': primary_used=True", primary_used)
    check(f"'{phrase}': response non-empty", bool(response) and len(response or "") > 20)
    resp_lower = (response or "").lower()
    check(f"'{phrase}': response has change info",
          "change" in resp_lower or "draft" in resp_lower or "differ" in resp_lower
          or "v1" in resp_lower or "v2" in resp_lower)
    # Must not be a source dump
    check(f"'{phrase}': no artifact_inventory", "artifact_inventory" not in resp_lower)
    check(f"'{phrase}': no live answer sources", "live answer sources:" not in resp_lower)

# ── Direct prototype validation ───────────────────────────────────────────────
loop = HermesCFOLoop()
response, trace = loop.process("what changed in the draft")
check("direct: intent=draft_comparison", trace["intent"] == "draft_comparison")
check("direct: tool=compare_drafts", trace["tool"] == "compare_drafts")
check("direct: response has diff info",
      "change" in response.lower() or "v1" in response.lower() or "v2" in response.lower())

# ── State is set to draft after comparison ────────────────────────────────────
loop2 = HermesCFOLoop()
loop2.process("what changed")
check("after draft comparison: state.last_response_was_draft=True",
      loop2.state.last_response_was_draft is True)

# ── "what is different from the last version" ────────────────────────────────
loop3 = HermesCFOLoop()
r3, t3 = loop3.process("what is different from the last version")
check("'what is different': intent=draft_comparison", t3["intent"] == "draft_comparison")

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C draft comparison: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
