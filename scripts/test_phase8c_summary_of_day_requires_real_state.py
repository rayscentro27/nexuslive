"""test_phase8c_summary_of_day_requires_real_state.py — summary_of_day uses real state or says unavailable."""
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
from prototypes import hermes_agentic_cfo_loop as proto

original_loader = proto._load_real_daily_summary

try:
    proto._load_real_daily_summary = lambda limit=5: {"state": None, "evidence": []}
    loop = HermesCFOLoop()
    response, trace = loop.process("what did we work on today")
    check("intent=summary_of_day", trace["intent"] == "summary_of_day")
    check("tool=show_daily_summary", trace["tool"] == "show_daily_summary")
    check("unavailable message returned", "i do not have a verified day summary yet" in response.lower())
    check("no mock marker in unavailable response", "based on mock data" not in response.lower())

    response2, used2 = run_cfo_limited_primary("what did we work on today")
    check("limited primary still used for honest unavailable", used2 is True)
    check("limited primary unavailable wording", "verified day summary" in (response2 or "").lower())

    proto._load_real_daily_summary = lambda limit=5: {
        "state": None,
        "evidence": [
            {
                "kind": "report",
                "summary": "Created grounded limited primary patch report",
                "path": "docs/reports/strategy/example.md",
            }
        ],
    }
    loop2 = HermesCFOLoop()
    response3, trace3 = loop2.process("daily summary")
    check("real summary includes evidence text", "created grounded limited primary patch report" in response3.lower())
    check("real summary avoids mock marker", "based on mock data" not in response3.lower())
    check("trace grounded true", trace3.get("grounded") is True)
finally:
    proto._load_real_daily_summary = original_loader
    os.environ.pop("HERMES_CFO_LOOP_MODE", None)
    os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C summary grounding: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
