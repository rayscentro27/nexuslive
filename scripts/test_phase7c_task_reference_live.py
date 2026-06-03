"""
test_phase7c_task_reference_live.py
Phase 7C tests: task and option references resolve from saved conversation state.
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


from lib.hermes_cfo_brain import (
    classify_cfo_intent,
    handle_task_reference,
    process_with_cfo_brain,
)
from lib.hermes_conversation_state import (
    update_conversation_state,
    load_conversation_state,
    save_conversation_state,
    _STATE_SCHEMA,
)

# ── Seed state with numbered items ────────────────────────────────────────────

seed_response = (
    "NEXUS PLAN\n\n"
    "Tasks for this week:\n\n"
    "1. Research affiliate programs for lead magnets\n"
    "2. Build landing page draft for Nexus membership\n"
    "3. Set up YouTube content calendar\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state(
    user_message="what are the tasks this week",
    hermes_response=seed_response,
    tool_used="nexus_plan",
)

# ── Task reference intent classification ──────────────────────────────────────

task_msgs = [
    "what was task 1", "what was task 2", "what was task 3",
    "what is task 1", "task 1", "task 2",
    "first task", "second task", "what were the tasks",
    "what was option 1", "the first option",
]
for msg in task_msgs:
    intent = classify_cfo_intent(msg)
    check(f"'{msg}' → task_reference or option_selection",
          intent in {"task_reference", "option_selection"})

# ── handle_task_reference resolves from state ────────────────────────────────

state = load_conversation_state()
r = handle_task_reference("what was task 1", state)
check("task ref returns string", isinstance(r, str))
check("task ref has PLAIN ANSWER header", "PLAIN ANSWER" in r)
check("task ref shows task text", "affiliate" in r.lower() or "task 1" in r.lower())
check("task ref has approval boundary", "approval" in r.lower())
check("task ref no evidence dump", "Live answer sources:" not in r)

r2 = handle_task_reference("what was task 2", state)
check("task 2 ref returns string", isinstance(r2, str))
check("task 2 shows landing page or task 2", "landing page" in r2.lower() or "task 2" in r2.lower())

# ── process_with_cfo_brain for task reference ─────────────────────────────────

r3 = process_with_cfo_brain("what was task 1", "what was task 1")
check("process: what was task 1 returns string", isinstance(r3, str) and len(r3) > 10)
check("process: PLAIN ANSWER in response", "PLAIN ANSWER" in (r3 or ""))
check("process: no evidence dump", "live answer sources:" not in (r3 or "").lower())
check("process: no quality fallback", "quality response" not in (r3 or "").lower())

r4 = process_with_cfo_brain("task 1", "task 1")
check("process: 'task 1' returns string", isinstance(r4, str) and len(r4) > 10)

# ── Task reference when no state ──────────────────────────────────────────────

# Hard-reset state (update_conversation_state now preserves prior context by design)
save_conversation_state(dict(_STATE_SCHEMA))
empty_state = load_conversation_state()
r5 = handle_task_reference("what was task 1", empty_state)
check("no-context task ref is graceful", isinstance(r5, str))
check("no-context has PLAIN ANSWER header", "PLAIN ANSWER" in r5)
check("no-context explains missing context", "don't have" in r5.lower() or "context" in r5.lower())
check("no-context no evidence dump", "Live answer sources:" not in r5)

# Print summary
print(f"\nPhase 7C task reference live: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
