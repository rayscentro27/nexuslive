"""test_phase8c_limited_primary_allowlist.py — allowlisted intents use CFO primary."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import (
    run_cfo_limited_primary, ALLOWLISTED_INTENTS, load_shadow_traces,
    clear_shadow_traces,
)

# Clear traces before test
clear_shadow_traces()

# ── Allowlisted test messages ─────────────────────────────────────────────────
test_cases = [
    ("create the implementation prompt now", "implementation_prompt_request"),
    ("what are all the scouts doing right now", "scout_status"),
    ("i approve them all", "approval_bulk_request"),
    ("do you understand my question", "acknowledgement_check"),
    ("implement it now", "implement_now"),
]

for message, expected_intent in test_cases:
    response, primary_used = run_cfo_limited_primary(message)
    check(f"'{message[:40]}': primary_used=True", primary_used is True)
    check(f"'{message[:40]}': response is non-empty", bool(response) and len(response or "") > 20)
    check(f"'{message[:40]}': response is string", isinstance(response, str))

# ── Trace has primary_used=True for allowlisted ───────────────────────────────
traces = load_shadow_traces(limit=50)
primary_traces = [t for t in traces if t.get("primary_used")]
check("at least some traces show primary_used=True", len(primary_traces) > 0)
for t in primary_traces:
    check(f"trace intent in allowlist: {t.get('cfo_intent')}", t.get("cfo_intent") in ALLOWLISTED_INTENTS)
    check("trace live_response_changed=True", t.get("live_response_changed") is True)
    check("trace mode=limited_primary", t.get("mode") == "limited_primary")

# ── Unknown/non-allowlisted intent falls through ──────────────────────────────
clear_shadow_traces()
response, primary_used = run_cfo_limited_primary("unknown_random_xyz_message_abc_not_matching")
# unknown_answer intent — may or may not be in allowlist
traces = load_shadow_traces(limit=10)
check("fallthrough trace is saved", len(traces) >= 1)
if traces:
    last = traces[-1]
    check("fallthrough trace has fallback_reason or primary_used",
          last.get("fallback_reason") is not None or last.get("primary_used") is False)

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C allowlist: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
