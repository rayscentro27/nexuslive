"""test_phase8c_implementation_prompt_uses_selected_option.py — implementation prompt uses selected option or asks clarification."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib import hermes_cfo_loop_shadow as shadow
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop

original_seed = shadow._seed_state_from_current

try:
    loop = HermesCFOLoop()
    loop.state.last_selected_option = 2
    loop.state.last_selected_option_text = "Patch Phase 8C grounding guard"
    response, trace = loop.process("create the implementation prompt now")
    check("direct intent=implementation_prompt_request", trace["intent"] == "implementation_prompt_request")
    check("selected option used", "patch phase 8c grounding guard" in response.lower())

    shadow._seed_state_from_current = lambda state: setattr(state, "last_selected_option_text", "Use the real approval queue")
    response2, used2 = shadow.run_cfo_limited_primary("create the implementation prompt now")
    check("limited primary used with selected option context", used2 is True)
    check("seeded selected option appears", "use the real approval queue" in (response2 or "").lower())

    shadow._seed_state_from_current = lambda state: None
    response3, used3 = shadow.run_cfo_limited_primary("create the implementation prompt now")
    check("limited primary still used for clarification", used3 is True)
    check("clarification returned when context missing", "what do you want me to implement" in (response3 or "").lower())
finally:
    shadow._seed_state_from_current = original_seed
    os.environ.pop("HERMES_CFO_LOOP_MODE", None)
    os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C implementation prompt grounding: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
