"""test_phase8c_limited_primary_scout_status.py — scout_status intent."""
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

# ── Scout status phrases ──────────────────────────────────────────────────────
phrases = [
    "what are all the scouts doing right now",
    "what are the scouts doing",
    "scout status",
]
for phrase in phrases:
    response, primary_used = run_cfo_limited_primary(phrase)
    check(f"'{phrase[:40]}': primary_used=True", primary_used)
    check(f"'{phrase[:40]}': response non-empty", bool(response) and len(response or "") > 20)
    resp_lower = (response or "").lower()
    # Must contain scout info
    check(f"'{phrase[:40]}': response mentions scout", "scout" in resp_lower)
    # Must NOT be a source intake dump
    check(f"'{phrase[:40]}': no artifact_inventory", "artifact_inventory" not in resp_lower)
    check(f"'{phrase[:40]}': no live answer sources", "live answer sources:" not in resp_lower)
    # Must NOT invent unverified completed research
    check(f"'{phrase[:40]}': no 'completed research' fabrication",
          "verified completed research" not in resp_lower)

# ── Direct prototype validation ───────────────────────────────────────────────
loop = HermesCFOLoop()
response, trace = loop.process("what are all the scouts doing right now")
check("direct: intent=scout_status", trace["intent"] == "scout_status")
check("direct: tool=show_scout_status", trace["tool"] == "show_scout_status")
check("direct: response contains scout info", "scout" in response.lower())
check("direct: response has assignment status", any(
    s in response.lower() for s in ("active", "queued", "completed")
))

# ── Response uses plain format, not raw data dump ─────────────────────────────
loop2 = HermesCFOLoop()
r2, t2 = loop2.process("all scouts")
check("all scouts: tool=show_scout_status", t2["tool"] == "show_scout_status")
r2_lower = r2.lower()
check("all scouts: no raw JSON artifacts", "{\"scout\":" not in r2)

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C scout status: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
