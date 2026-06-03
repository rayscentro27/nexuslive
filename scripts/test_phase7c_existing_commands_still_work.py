"""
test_phase7c_existing_commands_still_work.py
Phase 7C tests: Phase 6A-6F and Phase 7A/7B commands are not broken by Phase 7C changes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0


def check(label: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
from lib.hermes_cfo_brain import should_use_cfo_brain, classify_cfo_intent

# ── Exact commands still classify correctly through intake ────────────────────

exact_commands = [
    ("show approval queue",             "show_approval_queue"),
    ("show research queue",             "show_research_queue"),
    ("show scout assignments",          "show_scout_assignments"),
    ("show memory v2 primary status",   "memory_v2_primary_status"),
    ("daily operating cycle",           "daily_operating_cycle"),
    ("run daily operating cycle",       "daily_operating_cycle"),
    ("show failed responses",           "show_failed_responses"),
    ("log this as a bad response",      "log_bad_response"),
    ("hermes, learn from that",         "learn_from_that"),
    ("create tests from failures",      "create_tests_from_failures"),
]
for cmd, expected_intent in exact_commands:
    intent, _, _ = classify_intent(cmd)
    check(f"'{cmd}' → {expected_intent}", intent == expected_intent)

# ── CFO Brain does NOT intercept exact command phrases ───────────────────────

cfo_should_not_intercept = [
    "show approval queue",
    "run daily operating cycle",
    "show research queue",
    "build revenue asset packet",
    "show scout assignments",
    "show memory v2 primary status",
    "rescore revenue packet",
    "fix revenue packet assets",
    "show failed responses",
    "create tests from failures",
]
for cmd in cfo_should_not_intercept:
    check(f"CFO brain should NOT intercept '{cmd}'",
          not should_use_cfo_brain(cmd))

# ── Phase 7C forced intents DO NOT include exact command phrases ──────────────

_PHASE7C_FORCED_INTENTS = {
    "option_selection", "task_reference", "simplify_previous_response",
    "explain_previous_response", "morning_activity_question", "failure_feedback",
}
for cmd in cfo_should_not_intercept:
    intent = classify_cfo_intent(cmd)
    check(f"Phase 7C does NOT force-intercept '{cmd}'",
          intent not in _PHASE7C_FORCED_INTENTS)

# ── run_command still works for Phase 6 commands ─────────────────────────────

phase6_commands = [
    "show approval queue",
    "show research queue",
    "show scout assignments",
    "show failed responses",
]
for cmd in phase6_commands:
    r = run_command(cmd, source="telegram")
    check(f"run_command('{cmd}') returns string", isinstance(r, str) and len(r) > 5)
    # Note: 'show failed responses' intentionally shows logged evidence-dump failures
    if cmd != "show failed responses":
        check(f"run_command('{cmd}') no evidence dump", "Live answer sources:" not in (r or ""))

# ── Memory v2 commands still classify ────────────────────────────────────────

memory_v2_commands = [
    ("show memory v2 primary status", "memory_v2_primary_status"),
    ("memory v2 status",              "memory_v2_status"),
]
for cmd, expected in memory_v2_commands:
    intent, _, _ = classify_intent(cmd)
    check(f"'{cmd}' → {expected}", intent == expected)

# ── Daily operating cycle still classifies ───────────────────────────────────

intent_doc, _, _ = classify_intent("run daily operating cycle")
check("'run daily operating cycle' → daily_operating_cycle",
      intent_doc == "daily_operating_cycle")
check("CFO brain does not intercept 'hermes, run daily operating cycle'",
      not should_use_cfo_brain("hermes, run daily operating cycle"))

# ── 30-day revenue plan not intercepted by CFO brain ────────────────────────

check("CFO brain does not intercept '30 day revenue plan'",
      not should_use_cfo_brain("30 day revenue plan"))

# ── Approval decision routing not broken ─────────────────────────────────────

for cmd in ["approve item", "reject item"]:
    intent, _, _ = classify_intent(cmd)
    check(f"'{cmd}' classifies to approval intent",
          "approve" in intent or "reject" in intent)

# Print summary
print(f"\nPhase 7C existing commands still work: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
