"""test_phase8c_clarifying_question_primary.py — clarifying question prompt is primary-safe."""
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

from lib.hermes_cfo_loop_shadow import run_cfo_limited_primary
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop

loop = HermesCFOLoop()
response, trace = loop.process("ask me a better clarifying question")
check("intent=clarifying_question_request", trace["intent"] == "clarifying_question_request")
check("response header present", "clarifying question" in response.lower())
check("option 1 present", "1. create a safe implementation prompt" in response.lower())
check("option 4 present", "4. prepare approval checklist" in response.lower())

response2, used2 = run_cfo_limited_primary("ask me a better clarifying question")
check("limited primary used", used2 is True)
check("primary response contains clarifying question header", "clarifying question" in (response2 or "").lower())

os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C clarifying question: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
