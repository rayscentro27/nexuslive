"""test_phase8c_grounding_blocks_mock_primary.py — hard-block mock output in limited primary."""
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

from lib.hermes_cfo_loop_shadow import clear_shadow_traces, load_shadow_traces, run_cfo_limited_primary
from prototypes import hermes_agentic_cfo_loop as proto

clear_shadow_traces()

original_process = proto.HermesCFOLoop.process


def fake_process(self, message):
    return (
        "Based on mock data — live traces not loaded in prototype.\nBuild and publish lead magnet landing page.",
        {
            "trace_id": "fake1234",
            "intent": "summary_of_day",
            "confidence": 0.99,
            "tool": "show_daily_summary",
            "mode": "mock",
            "grounded": True,
            "grounded_data_paths_checked": ["docs/reports/operations/hermes_daily_cycle_state.json"],
        },
    )


proto.HermesCFOLoop.process = fake_process

try:
    response, primary_used = run_cfo_limited_primary("what did we work on today")
    check("mock response blocked from primary", primary_used is False)
    check("mock response not returned", response is None)

    traces = load_shadow_traces(limit=5)
    last = traces[-1] if traces else {}
    check("trace recorded", bool(last))
    check("trace marks mock_blocked", last.get("mock_blocked") is True)
    check("trace fallback reason=mock_output_blocked", last.get("fallback_reason") == "mock_output_blocked")
finally:
    proto.HermesCFOLoop.process = original_process
    os.environ.pop("HERMES_CFO_LOOP_MODE", None)
    os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C grounding block: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
