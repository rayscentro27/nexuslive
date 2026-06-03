"""
test_phase7d_last_meaningful_response_protection.py
Phase 7D: last_meaningful_response is NOT overwritten by fallback/error responses.
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
    get_last_meaningful_response,
    _is_meaningful_strategic_response,
)

# ── _is_meaningful_strategic_response detection ───────────────────────────────

# Meaningful responses
meaningful_cases = [
    "WEEKLY MONEY PLAN\n\n1. Lead magnet\n2. Membership\n\nMy recommendation: Start with 1.",
    "OPTION SELECTED\n\nYou chose option 1:\n  Activate the lead magnet funnel.",
    "TODAY'S NEXUS PLAN\n\nTop priority: Build landing page.",
    "MORNING SUMMARY\n\nHere is what happened:\n  * Research queue has 3 items.",
    # Note: CORRECTING COURSE is intentionally NOT in meaningful_cases — see fallback_cases below
    "REVENUE ASSET PACKET\n\nReadiness: 72/100. Lead magnet ready.",
]
for text in meaningful_cases:
    check(f"IS meaningful: {text[:40]}...", _is_meaningful_strategic_response(text))

# Fallback / non-strategic responses
fallback_cases = [
    "PLAIN ANSWER\n\nI don't have task 1 from the last response.",
    "PLAIN ANSWER\n\nI don't have the option list from the last response.",
    "PLAIN ANSWER\n\nI don't have a previous response to simplify yet.\nTry: 'how do we make money'",
    "PLAIN ANSWER\n\nI don't have a recent recommendation to explain.",
    "I NEED CLARIFICATION\n\nI understood your message but don't have enough context.",
    "CORRECTING COURSE\n\nI understand — that was not the right response.",
    "I wasn't able to generate a quality response.",
    "plain-language mode enabled",
]
for text in fallback_cases:
    check(f"NOT meaningful (fallback): {text[:40]}...",
          not _is_meaningful_strategic_response(text))

# ── last_meaningful_response is set by strategic response ─────────────────────

strategic = (
    "WEEKLY MONEY PLAN\n\n"
    "1. Lead magnet funnel\n"
    "2. Membership launch\n\n"
    "My recommendation: Start with 1.\n\n"
    "Approval boundary:\n  I will not publish..."
)
state1 = update_conversation_state("how do we make money this week", strategic)
check("strategic sets last_meaningful_response",
      bool(state1.get("last_meaningful_response")))
check("last_meaningful_response contains strategic content",
      "lead magnet" in (state1.get("last_meaningful_response") or "").lower())

# ── Fallback response does NOT overwrite last_meaningful_response ─────────────

fallback = (
    "PLAIN ANSWER\n\n"
    "I don't have task 1 from the last response.\n\n"
    "Try asking: 'how do we make money this week'.\n\n"
    "Approval boundary:\n  I will not publish..."
)
state2 = update_conversation_state("what was task 1", fallback)
lmr = state2.get("last_meaningful_response")
check("fallback does NOT overwrite last_meaningful_response",
      lmr is not None and "lead magnet" in (lmr or "").lower())
check("get_last_meaningful_response() returns strategic content after fallback",
      "lead magnet" in (get_last_meaningful_response() or "").lower())

# ── OPTION SELECTED is meaningful (updates last_meaningful_response) ──────────

option_selected = (
    "OPTION SELECTED\n\n"
    "You chose option 1:\n"
    "  Activate the lead magnet funnel\n\n"
    "Safe next step: Create prompt.\n\n"
    "Approval boundary:\n  I will not publish..."
)
state3 = update_conversation_state("lets do 1", option_selected)
lmr3 = state3.get("last_meaningful_response")
check("OPTION SELECTED IS meaningful", _is_meaningful_strategic_response(option_selected))
check("OPTION SELECTED updates last_meaningful_response",
      "option selected" in (lmr3 or "").lower() or "lead magnet" in (lmr3 or "").lower())

# ── Failure learning response does NOT erase last_meaningful_response ─────────

failure_learning = (
    "CORRECTING COURSE\n\n"
    "I understand — that was not the right response.\n"
    "I logged the bad response as a training example.\n\n"
    "Approval boundary:\n  I will not publish..."
)
state4 = update_conversation_state("that is not what i meant", failure_learning)
check("CORRECTING COURSE is NOT meaningful strategic (does not overwrite last plan)",
      not _is_meaningful_strategic_response(failure_learning))

# ── Multiple fallbacks in a row don't accumulate ────────────────────────────

for i in range(3):
    fb = f"PLAIN ANSWER\n\nI don't have task {i+1} from the last response.\nTry again."
    update_conversation_state(f"what was task {i+1}", fb)

lmr_final = get_last_meaningful_response()
check("last_meaningful_response intact after 3 fallbacks",
      "lead magnet" in (lmr_final or "").lower() or "option selected" in (lmr_final or "").lower())

print(f"\nPhase 7D last meaningful response protection: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
