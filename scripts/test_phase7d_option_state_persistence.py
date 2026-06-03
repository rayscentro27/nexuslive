"""
test_phase7d_option_state_persistence.py
Phase 7D: option map, task map, and recommendation persist across follow-up responses.
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


from lib.hermes_conversation_state import (
    update_conversation_state,
    load_conversation_state,
    get_option,
    get_task,
    get_last_recommendation,
    get_active_recommendation,
    mark_option_selected,
    get_selected_option_context,
)

# ── Step 1: Money strategy seeds option map ───────────────────────────────────

money_response = (
    "WEEKLY MONEY PLAN\n\n"
    "Revenue readiness score: 72/100\n\n"
    "Best money moves this week:\n\n"
    "1. Activate the funding readiness lead magnet funnel with an affiliate offer\n"
    "2. Launch Nexus membership at a founding-member price for early subscribers\n"
    "3. Run a YouTube/LinkedIn content push to build the email list first\n\n"
    "My recommendation:\n"
    "  Start with option 1 — it is closest to revenue with no upfront spend.\n"
    "  Say 'let's do 1' to select it.\n\n"
    "Approval boundary:\n  I will not publish..."
)
state1 = update_conversation_state(
    "how do we make money this week", money_response, tool_used="money_strategy"
)
check("step1: option_map has 3 items", len(state1.get("last_option_map", {})) == 3)
check("step1: option 1 is lead magnet",
      "lead magnet" in (state1.get("last_option_map", {}).get("1") or "").lower())
check("step1: recommendation set",
      "option 1" in (state1.get("last_recommendation") or "").lower())
check("step1: active_recommendation set",
      bool(state1.get("active_recommendation")))
check("step1: get_option(1) works",
      get_option(1) is not None and "lead magnet" in get_option(1).lower())
check("step1: get_active_recommendation() works",
      bool(get_active_recommendation()))

# ── Step 2: OPTION SELECTED response must NOT erase option map ────────────────

option_selected_response = (
    "OPTION SELECTED\n\n"
    "You chose option 1:\n"
    "  Activate the funding readiness lead magnet funnel with an affiliate offer\n\n"
    "Safe next step:\n"
    "  I can create an implementation prompt for this.\n\n"
    "Approval boundary:\n  I will not publish..."
)
state2 = update_conversation_state(
    "lets do 1", option_selected_response, tool_used="option_selection"
)
check("step2: option_map PRESERVED after OPTION SELECTED",
      len(state2.get("last_option_map", {})) == 3)
check("step2: option 1 still correct",
      "lead magnet" in (state2.get("last_option_map", {}).get("1") or "").lower())
check("step2: recommendation PRESERVED",
      bool(state2.get("last_recommendation")))
check("step2: active_recommendation PRESERVED",
      bool(state2.get("active_recommendation")))

# ── Step 3: mark_option_selected saves text, persists through next update ─────

mark_option_selected(1, text="Activate the funding readiness lead magnet funnel with an affiliate offer")
sel_num, sel_text = get_selected_option_context()
check("step3: selected_option_number = 1", sel_num == 1)
check("step3: selected_option_text is lead magnet", "lead magnet" in (sel_text or "").lower())

# Step 3b: update_conversation_state preserves selected option
state3 = update_conversation_state(
    "what was task 1", option_selected_response, tool_used="task_reference"
)
sel_num2, sel_text2 = get_selected_option_context()
check("step3b: selected_option_number preserved after update", sel_num2 == 1)
check("step3b: selected_option_text preserved after update",
      sel_text2 is not None and "lead magnet" in sel_text2.lower())

# ── Step 4: Fallback response must NOT erase option map ──────────────────────

fallback_response = (
    "PLAIN ANSWER\n\n"
    "I don't have task 1 from the last response.\n\n"
    "Try asking: 'how do we make money this week' to get a fresh option list.\n\n"
    "Approval boundary:\n  I will not publish..."
)
state4 = update_conversation_state(
    "what was task 1", fallback_response
)
check("step4: option_map NOT erased by fallback",
      len(state4.get("last_option_map", {})) == 3)
check("step4: recommendation NOT erased by fallback",
      bool(state4.get("last_recommendation")))
check("step4: active_recommendation NOT erased by fallback",
      bool(state4.get("active_recommendation")))
check("step4: selected_option_number NOT erased by fallback",
      state4.get("last_selected_option_number") == 1)
check("step4: selected_option_text NOT erased by fallback",
      "lead magnet" in (state4.get("last_selected_option_text") or "").lower())

# ── Step 5: get_option / get_task still work after all follow-ups ──────────────

check("step5: get_option(1) still works after follow-ups",
      get_option(1) is not None and "lead magnet" in get_option(1).lower())
check("step5: get_task(1) still works after follow-ups",
      get_task(1) is not None and "lead magnet" in get_task(1).lower())

print(f"\nPhase 7D option state persistence: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
