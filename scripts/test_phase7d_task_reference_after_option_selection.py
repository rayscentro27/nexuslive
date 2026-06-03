"""
test_phase7d_task_reference_after_option_selection.py
Phase 7D: "WHAT WAS TASK 1" resolves correctly after "LETS DO 1".
This is the exact live failure from the Telegram transcript.
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
    handle_money_strategy,
    handle_option_selection,
    handle_task_reference,
    process_with_cfo_brain,
)
from lib.hermes_conversation_state import (
    update_conversation_state,
    mark_option_selected,
    get_selected_option_context,
    load_conversation_state,
)

# ── Replicate exact live Telegram transcript ──────────────────────────────────

# Step 1: HOW DO WE MAKE MONEY THIS WEEK
money_response = (
    "WEEKLY MONEY PLAN\n\n"
    "1. Activate the funding readiness lead magnet funnel with an affiliate offer\n"
    "2. Launch Nexus membership at a founding-member price for early subscribers\n"
    "3. Run a YouTube/LinkedIn content push to build the email list first\n\n"
    "My recommendation:\n  Start with option 1.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state("how do we make money this week", money_response, tool_used="money_strategy")

# Step 2: LETS DO 1 — using process_with_cfo_brain (as the bot would)
r_option = process_with_cfo_brain("lets do 1", "lets do 1")
check("LETS DO 1 returns OPTION SELECTED", r_option is not None and "OPTION SELECTED" in (r_option or ""))
check("LETS DO 1 shows lead magnet", "lead magnet" in (r_option or "").lower())
check("LETS DO 1 no evidence dump", "Live answer sources:" not in (r_option or ""))

# Simulate what process_update does: calls update_conversation_state again with rendered output
update_conversation_state("lets do 1", r_option or "", tool_used="option_selection")

# Step 3: WHAT WAS TASK 1 — should resolve to option 1 text
r_task = process_with_cfo_brain("what was task 1", "what was task 1")
check("WHAT WAS TASK 1 returns string", isinstance(r_task, str) and len(r_task) > 10)
check("WHAT WAS TASK 1 has PLAIN ANSWER", "PLAIN ANSWER" in (r_task or ""))
check("WHAT WAS TASK 1 shows lead magnet text",
      "lead magnet" in (r_task or "").lower())
check("WHAT WAS TASK 1 no evidence dump", "Live answer sources:" not in (r_task or ""))
check("WHAT WAS TASK 1 no quality fallback",
      "quality response" not in (r_task or "").lower())
check("WHAT WAS TASK 1 not 'I don't have task 1'",
      "don't have task 1" not in (r_task or "").lower())

# ── Resolution order tests ────────────────────────────────────────────────────

state = load_conversation_state()
sel_num, sel_text = get_selected_option_context()

check("selected_option_number = 1 after LETS DO 1", sel_num == 1)
check("selected_option_text contains lead magnet", "lead magnet" in (sel_text or "").lower())

# handle_task_reference directly
state2 = load_conversation_state()
r2 = handle_task_reference("what was task 1", state2)
check("handle_task_reference: shows task text directly", "lead magnet" in r2.lower())
check("handle_task_reference: has approval boundary", "approval" in r2.lower())

# ── Various phrasings also resolve ───────────────────────────────────────────

for msg in ["what was option 1", "what was number 1", "remind me what 1 was", "task 1"]:
    r = process_with_cfo_brain(msg, msg)
    check(f"'{msg}' resolves to lead magnet text",
          r is not None and "lead magnet" in (r or "").lower())
    check(f"'{msg}' no evidence dump", "Live answer sources:" not in (r or ""))

print(f"\nPhase 7D task reference after option selection: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
