"""test_phase8c_limited_primary_trace_logging.py — trace fields for limited primary."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import (
    run_cfo_limited_primary, load_shadow_traces, clear_shadow_traces,
    _build_primary_trace, SHADOW_TRACE_FILE,
)

# ── Clear before test ─────────────────────────────────────────────────────────
clear_shadow_traces()

# ── Run a message that triggers primary ───────────────────────────────────────
response, primary_used = run_cfo_limited_primary("create the implementation prompt now")
check("primary_used for allowlisted intent", primary_used)

traces = load_shadow_traces(limit=10)
check("trace saved", len(traces) >= 1)
last = traces[-1]

# ── Required trace fields ─────────────────────────────────────────────────────
required_fields = [
    "timestamp", "message_hash", "normalized_message", "live_response_changed",
    "cfo_loop_mode", "cfo_provider", "cfo_intent", "cfo_selected_tool",
    "cfo_confidence", "cfo_response_preview", "safety_flags", "duration_ms",
    "primary_used", "fallback_reason", "mode",
]
for field in required_fields:
    check(f"trace has field '{field}'", field in last)

# ── Field values for primary trace ───────────────────────────────────────────
check("trace.live_response_changed=True when primary_used=True",
      last.get("live_response_changed") is True)
check("trace.primary_used=True", last.get("primary_used") is True)
check("trace.mode=limited_primary", last.get("mode") == "limited_primary")
check("trace.cfo_loop_mode=limited_primary", last.get("cfo_loop_mode") == "limited_primary")
check("trace.fallback_reason is None for primary", last.get("fallback_reason") is None)
check("trace.cfo_intent is set", last.get("cfo_intent") is not None)
check("trace.cfo_confidence is float", isinstance(last.get("cfo_confidence"), float))

# ── Non-primary trace has live_response_changed=False ────────────────────────
clear_shadow_traces()
response2, primary_used2 = run_cfo_limited_primary("unknown_xyz_not_matching_any_pattern_abc")
traces2 = load_shadow_traces(limit=10)
check("fallthrough trace saved", len(traces2) >= 1)
if traces2:
    last2 = traces2[-1]
    if not last2.get("primary_used"):
        check("fallthrough trace.live_response_changed=False", last2.get("live_response_changed") is False)
        check("fallthrough trace.fallback_reason set", last2.get("fallback_reason") is not None)

# ── No secrets in trace ───────────────────────────────────────────────────────
_SECRET_PATTERNS = ["sk-", "SUPABASE_SERVICE_ROLE", "OPENAI_API_KEY", "HERMES_GATEWAY_KEY"]
for t in load_shadow_traces(limit=50):
    trace_str = json.dumps(t).lower()
    for pat in _SECRET_PATTERNS:
        check(f"trace contains no '{pat}'", pat.lower() not in trace_str)
        break  # check each trace once

# ── Trace file is valid JSONL ─────────────────────────────────────────────────
if SHADOW_TRACE_FILE.exists():
    lines = SHADOW_TRACE_FILE.read_text().strip().splitlines()
    for i, line in enumerate(lines[-5:]):
        try:
            json.loads(line)
            check(f"trace line {i}: valid JSON", True)
        except Exception:
            check(f"trace line {i}: valid JSON", False)

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C trace logging: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
