"""test_phase8c_scout_status_requires_real_assignments.py — scout_status uses verified assignments or says unavailable."""
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

original_loader = proto._load_real_scout_snapshot

try:
    proto._load_real_scout_snapshot = lambda limit=10: {"assignments": [], "queue_entries": [], "action_assignments": []}
    loop = HermesCFOLoop()
    response, trace = loop.process("what are all the scouts doing right now")
    check("intent=scout_status", trace["intent"] == "scout_status")
    check("unavailable wording", "verified live scout assignments" in response.lower())
    check("no sample scout names", "research_scout_1" not in response.lower())

    proto._load_real_scout_snapshot = lambda limit=10: {
        "assignments": [{"scout": "funding_readiness_scout", "research_question": "Review checklist gaps", "status": "active"}],
        "queue_entries": [{"scout": "content_intelligence_scout", "question": "Review landing page copy", "status": "open"}],
        "action_assignments": [{"scout": "market_research_scout", "task": "Compare SMB segments", "status": "queued"}],
    }
    response2, used2 = run_cfo_limited_primary("what are all the scouts doing right now")
    text2 = (response2 or "").lower()
    check("limited primary used with real assignments", used2 is True)
    check("real scout name present", "funding_readiness_scout" in text2)
    check("sample scout name absent", "research_scout_1" not in text2)
finally:
    proto._load_real_scout_snapshot = original_loader
    os.environ.pop("HERMES_CFO_LOOP_MODE", None)
    os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C scout status grounding: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
