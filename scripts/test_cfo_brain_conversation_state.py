"""
test_cfo_brain_conversation_state.py
Phase 7B: CFO Brain — conversation state manager.
Verifies that state is saved, loaded, and follow-ups resolve correctly.
"""
import sys, os, json, time
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


from lib.hermes_conversation_state import (
    update_conversation_state, load_conversation_state,
    get_option, get_task, get_last_recommendation,
    get_last_response_full, get_last_response_summary,
    mark_option_selected, has_active_context, get_recent_history,
    _extract_numbered_list,
)

print("\nCFO Brain Conversation State Tests")
print("=" * 50)

print("\n-- _extract_numbered_list --")
TEXT_WITH_OPTIONS = """
1. Activate the lead magnet funnel
2. Add affiliate offer to funding checklist
3. Promote Nexus membership to funding-ready audience
"""
opts = _extract_numbered_list(TEXT_WITH_OPTIONS)
check("extracts dict", isinstance(opts, dict))
check("has key 1", 1 in opts)
check("has key 2", 2 in opts)
check("has key 3", 3 in opts)
check("key 1 has content", "lead magnet" in opts.get(1, "").lower())

TEXT_WITH_TASKS = """
Task 1: Fix the revenue packet score
Task 2: Review the approval queue
Option 3: Run the daily cycle
"""
tasks = _extract_numbered_list(TEXT_WITH_TASKS)
check("extracts task prefixes", len(tasks) >= 1)

print("\n-- update_conversation_state writes state --")
TEST_RESPONSE = """PLAIN ANSWER

Revenue readiness: 72/100.

What I can do next:
1. Activate the lead magnet funnel
2. Add affiliate offer
3. Promote Nexus membership

My recommendation: start with option 1.

Approval boundary: I will not publish without explicit Ray approval.
"""
update_conversation_state("how do we make money this week", TEST_RESPONSE, tool_used="revenue_asset_packet")
state = load_conversation_state()
check("state loaded", isinstance(state, dict))
check("last_user_message saved", "money" in state.get("last_user_message", "").lower())
check("last_hermes_response_full saved", state.get("last_hermes_response_full", "") != "")
check("last_recommendation saved", state.get("last_recommendation", "") != "")

print("\n-- get_option resolves numbered items --")
opt1 = get_option(1)
check("get_option(1) not None", opt1 is not None)
check("get_option(1) has content", len(opt1 or "") > 5)

print("\n-- get_last_response_full --")
full = get_last_response_full()
check("get_last_response_full not None", full is not None)
check("get_last_response_full has content", len(full or "") > 5)

print("\n-- get_last_recommendation --")
rec = get_last_recommendation()
check("get_last_recommendation not None", rec is not None)
check("get_last_recommendation has content", len(rec or "") > 3)

print("\n-- mark_option_selected --")
mark_option_selected(1)
state2 = load_conversation_state()
check("last_selected_option saved", state2.get("last_selected_option") == 1)

print("\n-- has_active_context --")
active = has_active_context()
check("has_active_context returns bool", isinstance(active, bool))
check("active context is True after update", active is True)

print("\n-- get_recent_history --")
history = get_recent_history(3)
check("recent history is list", isinstance(history, list))

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
