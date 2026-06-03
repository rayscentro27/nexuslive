"""test_phase8c_limited_primary_acknowledgement.py — acknowledgement_check intent."""
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

# ── Acknowledgement phrases ───────────────────────────────────────────────────
phrases = [
    "do you understand my question",
    "did you understand",
    "do you understand",
]
for phrase in phrases:
    response, primary_used = run_cfo_limited_primary(phrase)
    check(f"'{phrase}': primary_used=True", primary_used)
    check(f"'{phrase}': response non-empty", bool(response) and len(response or "") > 10)
    resp_lower = (response or "").lower()
    check(f"'{phrase}': response contains 'understand'",
          "understand" in resp_lower or "understood" in resp_lower)
    # Must not be a source intake dump
    check(f"'{phrase}': no 'live answer sources'", "live answer sources:" not in resp_lower)
    check(f"'{phrase}': no 'artifact_inventory'", "artifact_inventory" not in resp_lower)
    check(f"'{phrase}': no 'hermes report' dump", resp_lower.count("hermes report") <= 1)

# ── Direct prototype validation ───────────────────────────────────────────────
loop = HermesCFOLoop()
response, trace = loop.process("do you understand my question")
check("direct: intent=acknowledgement_check", trace["intent"] == "acknowledgement_check")
check("direct: tool=plain_acknowledgement", trace["tool"] == "plain_acknowledgement")
check("direct: response has 'understand'", "understand" in response.lower())

# ── "ask me a better clarifying question" — plain followup ───────────────────
loop2 = HermesCFOLoop()
response2, trace2 = loop2.process("ask me a better clarifying question")
check("clarifying question: response non-empty", bool(response2) and len(response2) > 10)

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C acknowledgement: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
