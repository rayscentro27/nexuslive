"""
test_phase7c_live_runtime_trace.py
Phase 7C tests: debug trace script runs and produces correct routing records.
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


# ── Imports ───────────────────────────────────────────────────────────────────

from lib.hermes_cfo_brain import (
    classify_cfo_intent,
    should_use_cfo_brain,
    process_with_cfo_brain,
)
from lib.hermes_conversation_state import (
    load_conversation_state,
    get_option,
    get_task,
    get_last_recommendation,
    get_last_response_full,
)

# ── Phase 7C critical messages classify correctly ─────────────────────────────

check("LETS DO 1 → option_selection", classify_cfo_intent("lets do 1") == "option_selection")
check("LET'S DO 1 → option_selection", classify_cfo_intent("let's do 1") == "option_selection")
check("WHAT WAS TASK 1 → task_reference", classify_cfo_intent("what was task 1") == "task_reference")
check("CAN YOU SIMPLIFY YOUR RESPONSE → simplify", classify_cfo_intent("can you simplify your response") == "simplify_previous_response")
check("EXPLAIN YOUR RECOMMENDATION → explain", classify_cfo_intent("explain your recommendation in plain language") == "explain_previous_response")
check("WHAT DID YOU DO THIS MORNING → morning", classify_cfo_intent("what did you do this morning") == "morning_activity_question")
check("THAT IS NOT WHAT I MEANT → failure_feedback", classify_cfo_intent("that is not what i meant") == "failure_feedback")
check("HOW DO WE MAKE MONEY → money_strategy", classify_cfo_intent("how do we make money this week") == "money_strategy_question")

# ── should_use_cfo_brain is True for critical messages ───────────────────────

check("should_use_cfo_brain: lets do 1", should_use_cfo_brain("lets do 1"))
check("should_use_cfo_brain: what was task 1", should_use_cfo_brain("what was task 1"))
check("should_use_cfo_brain: can you simplify your response", should_use_cfo_brain("can you simplify your response"))
check("should_use_cfo_brain: explain your recommendation in plain language", should_use_cfo_brain("explain your recommendation in plain language"))
check("should_use_cfo_brain: what did you do this morning", should_use_cfo_brain("what did you do this morning"))
check("should_use_cfo_brain: that is not what i meant", should_use_cfo_brain("that is not what i meant"))
check("should_use_cfo_brain: how do we make money this week", should_use_cfo_brain("how do we make money this week"))

# ── should_use_cfo_brain returns False for exact commands ────────────────────

check("NOT cfo_brain: show approval queue", not should_use_cfo_brain("show approval queue"))
check("NOT cfo_brain: run daily operating cycle", not should_use_cfo_brain("run daily operating cycle"))
check("NOT cfo_brain: show research queue", not should_use_cfo_brain("show research queue"))
check("NOT cfo_brain: build revenue asset packet", not should_use_cfo_brain("build revenue asset packet"))

# ── process_with_cfo_brain returns non-None for critical messages ─────────────

r = process_with_cfo_brain("what did you do this morning", "what did you do this morning")
check("morning_activity returns string", isinstance(r, str) and len(r) > 10)
check("morning_activity no evidence dump", "Live answer sources:" not in (r or ""))
check("morning_activity no quality fallback", "quality response" not in (r or "").lower())

r2 = process_with_cfo_brain("that is not what i meant", "that is not what i meant")
check("failure_feedback returns string", isinstance(r2, str) and len(r2) > 10)
check("failure_feedback has CORRECTING COURSE or PLAIN ANSWER", "CORRECTING" in (r2 or "").upper() or "PLAIN ANSWER" in (r2 or ""))

r3 = process_with_cfo_brain("how do we make money this week", "how do we make money this week")
check("money_strategy returns string", isinstance(r3, str) and len(r3) > 20)
check("money_strategy has numbered options", "1." in (r3 or "") or "1:" in (r3 or ""))
check("money_strategy no evidence dump", "Live answer sources:" not in (r3 or ""))

# ── Conversation state loads correctly ────────────────────────────────────────

state = load_conversation_state()
check("load_conversation_state returns dict", isinstance(state, dict))
check("state has last_option_map key", "last_option_map" in state)
check("state has last_task_map key", "last_task_map" in state)
check("state has current_topic key", "current_topic" in state)

# Print summary
print(f"\nPhase 7C live runtime trace: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
