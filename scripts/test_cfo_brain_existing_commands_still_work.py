"""
test_cfo_brain_existing_commands_still_work.py
Phase 7B: CFO Brain — existing commands still work.
Verifies that Phase 7B does not break Phase 6A–7A commands
and that should_use_cfo_brain returns False for exact commands.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passes = 0
failures = 0

def check(label, cond):
    global passes, failures
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures += 1
    else:
        passes += 1
    print(f"  [{status}] {label}")
    return cond


from lib.hermes_cfo_brain import should_use_cfo_brain

print("\nCFO Brain — Existing Commands Still Work Tests")
print("=" * 60)

print("\n-- should_use_cfo_brain returns False for exact commands --")
_EXACT_COMMANDS = [
    "show approval queue",
    "run daily operating cycle",
    "build revenue asset packet",
    "show revenue asset packet",
    "show research queue",
    "show scout assignments",
    "show pending items",
    "show failed responses",
    "rescore revenue packet",
    "fix revenue packet assets",
    "show asset fix report",
    "show last daily plan",
    "show unresolved questions",
    "dedupe research queue",
    "approve item 1",
    "reject item 2",
    "show memory v2 primary status",
    "show learning loop",
    "list agents",
    "show approval queue",
    "record lesson learned",
    "mark item 1 complete",
    "show cfo notes",
]
for cmd in _EXACT_COMMANDS:
    check(f"'{cmd}' → brain=False", should_use_cfo_brain(cmd) is False)

print("\n-- Intake classifier has Phase 7B intents --")
try:
    from hermes_command_router.intake import classify_intent
    _7B_COMMANDS = [
        ("show failed responses", "show_failed_responses"),
        ("log this as a bad response", "log_bad_response"),
        ("hermes, learn from that", "learn_from_that"),
        ("create tests from failures", "create_tests_from_failures"),
    ]
    for cmd, expected_intent in _7B_COMMANDS:
        intent, _, _ = classify_intent(cmd)
        check(f"'{cmd}' → intent={expected_intent}", intent == expected_intent)
except Exception as e:
    check(f"intake classify_intent: {e}", False)

print("\n-- Router has Phase 7B handlers --")
try:
    from hermes_command_router.router import _PLAIN_INTENTS
    for intent in ["show_failed_responses", "log_bad_response",
                   "learn_from_that", "create_tests_from_failures"]:
        check(f"handler exists: {intent}", intent in _PLAIN_INTENTS)
except Exception as e:
    check(f"router _PLAIN_INTENTS: {e}", False)

print("\n-- Phase 6A–7A intents still in _PLAIN_INTENTS --")
_CRITICAL_INTENTS = [
    "daily_operating_cycle",
    "show_approval_queue",
    "build_revenue_asset_packet",
    "show_research_queue",
    "memory_v2_primary_status",
    "lesson_record",
    "dedupe_research_queue",
]
try:
    from hermes_command_router.router import _PLAIN_INTENTS
    for intent in _CRITICAL_INTENTS:
        check(f"handler exists: {intent}", intent in _PLAIN_INTENTS)
except Exception as e:
    check(f"router handlers: {e}", False)

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
