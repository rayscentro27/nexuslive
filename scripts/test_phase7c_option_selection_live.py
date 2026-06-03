"""
test_phase7c_option_selection_live.py
Phase 7C tests: option selection resolves from saved conversation state.
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
    should_use_cfo_brain,
    handle_option_selection,
    process_with_cfo_brain,
)
from lib.hermes_conversation_state import (
    update_conversation_state,
    load_conversation_state,
)

# ── Seed the state with a money strategy response ─────────────────────────────

seed_response = (
    "WEEKLY MONEY PLAN\n\n"
    "Revenue readiness score: 72/100\n\n"
    "Best money moves this week:\n\n"
    "1. Activate the lead magnet funnel with an affiliate offer\n"
    "2. Launch Nexus membership at founding-member price\n"
    "3. Run a YouTube/LinkedIn content push\n\n"
    "My recommendation:\n"
    "  Start with option 1 — closest to revenue.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state(
    user_message="how do we make money this week",
    hermes_response=seed_response,
    tool_used="money_strategy",
)

# ── Option selection intent classification ────────────────────────────────────

option_msgs = [
    "lets do 1", "let's do 1", "let's do 2", "lets do 3",
    "do option 1", "choose option 2", "go with option 1",
    "option 1", "option 2", "i'll choose 1", "select option 1",
    "pick 1", "pick 2",
]
for msg in option_msgs:
    check(f"'{msg}' → option_selection", classify_cfo_intent(msg) == "option_selection")

# ── should_use_cfo_brain for option selection phrases ────────────────────────

check("should_use_cfo_brain: lets do 1", should_use_cfo_brain("lets do 1"))
check("should_use_cfo_brain: let's do 2", should_use_cfo_brain("let's do 2"))
check("should_use_cfo_brain: option 1", should_use_cfo_brain("option 1"))

# ── handle_option_selection resolves from state ───────────────────────────────

state = load_conversation_state()
r = handle_option_selection("lets do 1", state)
check("option selection returns string", isinstance(r, str))
check("option selection has OPTION SELECTED", "OPTION SELECTED" in r)
check("option selection shows option text", "lead magnet" in r.lower())
check("option selection shows chosen number", "1" in r)
check("option selection has approval boundary", "approval" in r.lower())
check("option selection no evidence dump", "Live answer sources:" not in r)

r2 = handle_option_selection("let's do 2", state)
check("option 2 selection returns string", isinstance(r2, str))
check("option 2 shows membership", "membership" in r2.lower())

# ── process_with_cfo_brain for option selection ───────────────────────────────

r3 = process_with_cfo_brain("lets do 1", "lets do 1")
check("process: lets do 1 returns string", isinstance(r3, str) and len(r3) > 10)
check("process: lets do 1 has OPTION SELECTED", "OPTION SELECTED" in (r3 or ""))
check("process: no quality fallback", "quality response" not in (r3 or "").lower())
check("process: no evidence dump", "live answer sources:" not in (r3 or "").lower())

r4 = process_with_cfo_brain("let's do 1", "let's do 1")
check("process: let's do 1 returns string", isinstance(r4, str) and len(r4) > 10)

# ── Option selection when no state exists ────────────────────────────────────

update_conversation_state(
    user_message="test reset",
    hermes_response="no options here",
    tool_used=None,
)
empty_state = load_conversation_state()
r5 = handle_option_selection("lets do 1", empty_state)
check("no-context option selection is graceful", isinstance(r5, str))
check("no-context has OPTION SELECTED header", "OPTION SELECTED" in r5)
check("no-context explains missing state", "don't have" in r5.lower() or "no" in r5.lower())
check("no-context no evidence dump", "Live answer sources:" not in r5)

# Print summary
print(f"\nPhase 7C option selection live: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
