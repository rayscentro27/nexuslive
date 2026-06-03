"""test_phase8b_cfo_shadow_no_live_response_change.py — Shadow never changes live response."""
import sys, os, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

from pathlib import Path

os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import (
    run_cfo_shadow_for_message, build_shadow_trace, SHADOW_TRACE_DIR,
)

# ── build_shadow_trace always has live_response_changed=False ─────────────────
for msg in ["how do we make money", "lets do 1", "what was task 1", "implement it"]:
    trace = build_shadow_trace(
        message=msg,
        live_response="WEEKLY MONEY PLAN\n\n1. Lead magnet\n2. Membership",
        cfo_result=None,
        error=None,
    )
    check(f"live_response_changed=False for: {msg[:30]}", trace["live_response_changed"] is False)

# ── run_cfo_shadow_for_message returns trace with live_response_changed=False ─
with tempfile.TemporaryDirectory() as tmpdir:
    import lib.hermes_cfo_loop_shadow as shadow_mod
    orig_file = shadow_mod.SHADOW_TRACE_FILE
    tmp_trace = Path(tmpdir) / "traces.jsonl"
    shadow_mod.SHADOW_TRACE_FILE = tmp_trace
    shadow_mod.SHADOW_TRACE_DIR.mkdir(parents=True, exist_ok=True)

    trace = run_cfo_shadow_for_message(
        "how do we make money this week",
        live_response="WEEKLY MONEY PLAN\n\nHere are your options.",
    )
    check("run: live_response_changed=False", trace.get("live_response_changed") is False)
    check("run: returns dict", isinstance(trace, dict))
    check("run: has cfo_intent", "cfo_intent" in trace)
    check("run: has cfo_selected_tool", "cfo_selected_tool" in trace)
    check("run: mode is shadow", trace.get("cfo_loop_mode") == "shadow")

    shadow_mod.SHADOW_TRACE_FILE = orig_file

# ── run_cfo_shadow_for_message does not return the live response ──────────────
live = "THIS IS THE LIVE RESPONSE FROM PHASE 7D"
trace2 = run_cfo_shadow_for_message("test message", live_response=live)
check("shadow does not return live response text", trace2.get("cfo_response_preview", "") != live)
check("live_response_changed still False after shadow run", trace2.get("live_response_changed") is False)

# ── run_cfo_shadow_async is fire-and-forget (does not raise) ──────────────────
import time
from lib.hermes_cfo_loop_shadow import run_cfo_shadow_async
try:
    run_cfo_shadow_async("test async message", live_response="live resp")
    time.sleep(0.1)
    check("run_cfo_shadow_async does not raise", True)
except Exception as e:
    check("run_cfo_shadow_async does not raise", False)

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8B no live response change: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
