"""
test_phase7d_simplify_uses_meaningful_response.py
Phase 7D: CAN YOU SIMPLIFY YOUR RESPONSE uses last_meaningful_response,
not the most-recent fallback/task-missing response.
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


from lib.hermes_cfo_brain import handle_simplify_request, process_with_cfo_brain
from lib.hermes_conversation_state import (
    update_conversation_state,
    get_last_meaningful_response,
    load_conversation_state,
    mark_option_selected,
)

# ── Step 1: Seed with money strategy ─────────────────────────────────────────

money = (
    "WEEKLY MONEY PLAN\n\n"
    "Revenue readiness score: 72/100\n\n"
    "Best money moves this week:\n\n"
    "1. Activate the funding readiness lead magnet funnel with an affiliate offer\n"
    "2. Launch Nexus membership at a founding-member price\n"
    "3. Run a YouTube/LinkedIn content push\n\n"
    "My recommendation:\n  Start with option 1.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state("how do we make money this week", money, tool_used="money_strategy")
check("seed: last_meaningful_response is money plan",
      "lead magnet" in (get_last_meaningful_response() or "").lower())

# ── Step 2: LETS DO 1 ────────────────────────────────────────────────────────

option_selected = (
    "OPTION SELECTED\n\nYou chose option 1:\n"
    "  Activate the funding readiness lead magnet funnel with an affiliate offer\n\n"
    "Approval boundary:\n  I will not publish..."
)
mark_option_selected(1, text="Activate the funding readiness lead magnet funnel with an affiliate offer")
update_conversation_state("lets do 1", option_selected, tool_used="option_selection")

# ── Step 3: WHAT WAS TASK 1 returns fallback (simulated bad case) ──────────────

# Simulate what happens if task reference returns no-context (shouldn't happen now, but test robustness)
task_fallback = (
    "PLAIN ANSWER\n\n"
    "I don't have task 1 from the last response.\n\n"
    "Try asking: 'how do we make money this week'.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state("what was task 1", task_fallback)
check("step3: last_meaningful_response NOT overwritten by task fallback",
      "lead magnet" in (get_last_meaningful_response() or "").lower()
      or "option selected" in (get_last_meaningful_response() or "").lower())

# ── Step 4: CAN YOU SIMPLIFY YOUR RESPONSE should use meaningful content ───────

state = load_conversation_state()
r = handle_simplify_request("can you simplify your response", state)

check("simplify returns string", isinstance(r, str) and len(r) > 10)
check("simplify no evidence dump", "Live answer sources:" not in r)
check("simplify no quality fallback", "quality response" not in r.lower())
check("simplify does NOT simplify the task-missing fallback",
      "don't have task 1" not in r.lower())
check("simplify no 'I don't have a previous response to simplify yet'",
      "don't have a previous response to simplify yet" not in r.lower()
      or "lead magnet" in r.lower() or "money" in r.lower())

# ── process_with_cfo_brain for simplify ───────────────────────────────────────

r2 = process_with_cfo_brain("can you simplify your response", "can you simplify your response")
check("process: simplify returns string", isinstance(r2, str) and len(r2) > 10)
check("process: simplify no evidence dump", "Live answer sources:" not in (r2 or ""))
check("process: simplify no quality fallback", "quality response" not in (r2 or "").lower())
check("process: simplify does not simplify task-missing fallback",
      "don't have task 1" not in (r2 or "").lower())

# ── Simplify with truly no prior context returns graceful message ─────────────

# Reset to completely fresh state
update_conversation_state(
    "test reset",
    "PLAIN ANSWER\n\nI don't have a previous response to simplify yet. Please ask me a question first.",
    tool_used=None,
)
# Force last_meaningful_response to None by checking fresh load
from lib.hermes_conversation_state import _STATE_PATH, _STRATEGY_DIR
import json
_STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
import time
fresh_state = {
    "last_user_message": "test",
    "last_hermes_response_full": "PLAIN ANSWER\n\nI don't have a previous response to simplify yet.",
    "last_meaningful_response": None,
    "last_meaningful_response_summary": None,
    "last_option_map": {},
    "last_recommendation": None,
    "active_recommendation": None,
    "last_selected_option_number": None,
    "last_selected_option_text": None,
    "updated_at": "2026-06-03T10:00:00+00:00",
    "created_at": "2026-06-03T10:00:00+00:00",
    "stale_after_hours": 24,
}
_STATE_PATH.write_text(json.dumps(fresh_state, indent=2))

state_fresh = load_conversation_state()
r3 = handle_simplify_request("can you simplify your response", state_fresh)
check("no-context simplify returns graceful message", isinstance(r3, str) and len(r3) > 10)
check("no-context simplify has PLAIN ANSWER", "PLAIN ANSWER" in r3)
check("no-context simplify no evidence dump", "Live answer sources:" not in r3)

print(f"\nPhase 7D simplify uses meaningful response: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
