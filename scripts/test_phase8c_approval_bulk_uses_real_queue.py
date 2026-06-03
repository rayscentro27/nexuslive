"""test_phase8c_approval_bulk_uses_real_queue.py — approval bulk uses real queue or says unavailable."""
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

original_loader = proto._load_real_approval_items

try:
    proto._load_real_approval_items = lambda limit=10: []
    loop = HermesCFOLoop()
    response, trace = loop.process("i approve them all")
    check("intent=approval_bulk_request", trace["intent"] == "approval_bulk_request")
    check("queue unavailable wording", "approval queue is unavailable" in response.lower())

    proto._load_real_approval_items = lambda limit=10: [
        {"title": "Approve checklist draft public use", "risk_level": "low"},
        {"title": "Approve affiliate insertion", "risk_level": "high"},
    ]
    response2, used2 = run_cfo_limited_primary("i approve them all")
    text2 = (response2 or "").lower()
    check("limited primary used", used2 is True)
    check("real queue title present", "approve checklist draft public use" in text2)
    check("high risk skipped called out", "approve affiliate insertion" in text2)
    check("no mock affiliate application title", "apply to funding affiliate program" not in text2)
finally:
    proto._load_real_approval_items = original_loader
    os.environ.pop("HERMES_CFO_LOOP_MODE", None)
    os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C approval bulk grounding: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
