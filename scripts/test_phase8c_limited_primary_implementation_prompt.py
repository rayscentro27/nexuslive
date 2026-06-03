"""test_phase8c_limited_primary_implementation_prompt.py — implementation prompt request."""
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

# ── "create the implementation prompt now" ────────────────────────────────────
phrases = [
    "create the implementation prompt now",
    "implementation prompt now",
    "write the implementation prompt",
]
for phrase in phrases:
    response, primary_used = run_cfo_limited_primary(phrase)
    check(f"'{phrase[:40]}': primary_used=True", primary_used)
    check(f"'{phrase[:40]}': response non-empty", bool(response) and len(response or "") > 20)
    resp_lower = (response or "").lower()
    check(f"'{phrase[:40]}': contains IMPLEMENTATION PROMPT", "implementation prompt" in resp_lower)
    check(f"'{phrase[:40]}': does not say 'published to'", "published to" not in resp_lower)
    check(f"'{phrase[:40]}': does not say 'deployed to production'", "deployed to production" not in resp_lower)
    check(f"'{phrase[:40]}': does not say 'activated payment'", "activated payment" not in resp_lower)
    check(f"'{phrase[:40]}': has internal only note or safety note",
          "internal" in resp_lower or "ray approval" in resp_lower or "safe" in resp_lower)

# ── Direct prototype validation ───────────────────────────────────────────────
loop = HermesCFOLoop()
response, trace = loop.process("create the implementation prompt now")
check("direct: intent=implementation_prompt_request", trace["intent"] == "implementation_prompt_request")
check("direct: tool=create_implementation_prompt", trace["tool"] == "create_implementation_prompt")
check("direct: IMPLEMENTATION PROMPT in response", "implementation prompt" in response.lower())

# ── implement_now also triggers implementation prompt ─────────────────────────
loop2 = HermesCFOLoop()
response2, trace2 = loop2.process("implement it now")
check("implement_now: intent is implement_now or implementation_prompt_request",
      trace2["intent"] in ("implement_now", "implementation_prompt_request"))
check("implement_now: tool is create_implementation_prompt", trace2["tool"] == "create_implementation_prompt")
check("implement_now: implementation prompt in response", "implementation prompt" in response2.lower())

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C implementation prompt: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
