"""
test_phase7c_plain_language_recommendation_live.py
Phase 7C tests: explain recommendation returns plain answer, not evidence dump.
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
    handle_explain_request,
    process_with_cfo_brain,
)
from lib.hermes_conversation_state import update_conversation_state, load_conversation_state

# ── explain intent classification ─────────────────────────────────────────────

explain_msgs = [
    "explain your recommendation in plain language",
    "explain your recommendation",
    "what does that mean",
    "and what does that mean",
    "what do you mean",
    "explain that",
    "explain in plain",
    "in plain language",
    "plain language explanation",
    "explain the recommendation",
]
for msg in explain_msgs:
    intent = classify_cfo_intent(msg)
    check(f"'{msg}' → explain or plain_language",
          intent in {"explain_previous_response", "plain_language_request"})

check("should_use: explain recommendation in plain language",
      should_use_cfo_brain("explain your recommendation in plain language"))

# ── With meaningful context, returns PLAIN ANSWER (not evidence dump) ─────────

seed = (
    "WEEKLY MONEY PLAN\n\n"
    "1. Activate the lead magnet funnel\n"
    "2. Launch Nexus membership\n"
    "3. Run content push\n\n"
    "My recommendation:\n"
    "  Start with option 1 — closest to revenue.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state(
    user_message="how do we make money this week",
    hermes_response=seed,
    tool_used="money_strategy",
)

state = load_conversation_state()
r = handle_explain_request("explain your recommendation in plain language", state)
check("explain returns string", isinstance(r, str) and len(r) > 10)
check("explain has PLAIN ANSWER", "PLAIN ANSWER" in r)
check("explain no evidence dump", "Live answer sources:" not in r)
check("explain no quality fallback", "quality response" not in r.lower())
check("explain no 'plain-language mode enabled'", "plain-language mode enabled" not in r.lower())
check("explain has approval boundary", "approval" in r.lower())

# ── With option_map context, explains the first option ───────────────────────

check("explain uses option map when no explicit rec",
      "lead magnet" in r.lower() or "option" in r.lower() or "recommendation" in r.lower())

# ── With no prior context, returns graceful no-context message ───────────────

update_conversation_state(
    user_message="test reset",
    hermes_response="PLAIN ANSWER\n\nI don't have a recent recommendation to explain.",
    tool_used=None,
)
empty_state = load_conversation_state()
r_empty = handle_explain_request("explain your recommendation", empty_state)
check("no-context explain returns string", isinstance(r_empty, str))
check("no-context explain has PLAIN ANSWER", "PLAIN ANSWER" in r_empty)
check("no-context explain no evidence dump", "Live answer sources:" not in r_empty)
check("no-context explain no quality fallback", "quality response" not in r_empty.lower())

# ── process_with_cfo_brain for explain ────────────────────────────────────────

# Re-seed meaningful state
update_conversation_state(
    user_message="how do we make money this week",
    hermes_response=seed,
    tool_used="money_strategy",
)
r2 = process_with_cfo_brain("explain your recommendation in plain language",
                             "explain your recommendation in plain language")
check("process: explain returns string", isinstance(r2, str) and len(r2) > 10)
check("process: PLAIN ANSWER in response", "PLAIN ANSWER" in (r2 or ""))
check("process: no evidence dump", "live answer sources:" not in (r2 or "").lower())
check("process: no quality fallback", "quality response" not in (r2 or "").lower())

r3 = process_with_cfo_brain("what does that mean", "what does that mean")
check("process: 'what does that mean' returns string", isinstance(r3, str) and len(r3) > 10)
check("process: 'what does that mean' no evidence dump",
      "live answer sources:" not in (r3 or "").lower())

# Print summary
print(f"\nPhase 7C plain language recommendation live: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
