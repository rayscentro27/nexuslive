"""
test_phase7c_simplify_followup_live.py
Phase 7C tests: simplify follow-up uses meaningful prior response, not default template.
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
    handle_simplify_request,
    process_with_cfo_brain,
    _is_meaningful_response,
)
from lib.hermes_conversation_state import update_conversation_state, load_conversation_state

# ── _is_meaningful_response correctly identifies content ─────────────────────

check("meaningful: long content", _is_meaningful_response("Revenue score 72. This is a great option to pursue."))
check("not meaningful: empty", not _is_meaningful_response(""))
check("not meaningful: short", not _is_meaningful_response("Hi"))
check("not meaningful: no-context template",
      not _is_meaningful_response("I don't have a previous response to simplify yet."))
check("not meaningful: ask me first",
      not _is_meaningful_response("Please ask me a question first then I can help."))
check("meaningful: long response with options",
      _is_meaningful_response("WEEKLY MONEY PLAN\n\n1. Lead magnet\n2. Membership\n3. Content push\n\nMy recommendation: Start with 1."))

# ── simplify intent classification ────────────────────────────────────────────

simplify_msgs = [
    "can you simplify your response",
    "simplify that",
    "make it simpler",
    "shorter version",
    "too long",
    "shorten that",
    "simpler version",
    "can you simplify",
    "simplify the response",
    "brief version",
    "summarize that",
]
for msg in simplify_msgs:
    check(f"'{msg}' → simplify_previous_response",
          classify_cfo_intent(msg) == "simplify_previous_response")

check("should_use_cfo_brain: can you simplify your response",
      should_use_cfo_brain("can you simplify your response"))

# ── Simplify with no prior context returns graceful message ───────────────────

# Reset state to no meaningful content
update_conversation_state(
    user_message="test",
    hermes_response="PLAIN ANSWER\n\nPlease ask me a question first then I can help.",
    tool_used=None,
)
state = load_conversation_state()
r_no_ctx = handle_simplify_request("can you simplify your response", state)
check("no-context simplify returns string", isinstance(r_no_ctx, str))
check("no-context simplify has PLAIN ANSWER", "PLAIN ANSWER" in r_no_ctx)
check("no-context simplify no evidence dump", "Live answer sources:" not in r_no_ctx)
check("no-context simplify no quality fallback", "quality response" not in r_no_ctx.lower())
check("no-context simplify explains no prior", "don't have" in r_no_ctx.lower() or "no previous" in r_no_ctx.lower())

# ── Simplify with meaningful prior context uses the content ───────────────────

meaningful_response = (
    "WEEKLY MONEY PLAN\n\n"
    "Revenue readiness score: 72/100\n\n"
    "Best money moves this week:\n\n"
    "1. Activate the lead magnet funnel with an affiliate offer\n"
    "2. Launch Nexus membership at founding-member price\n"
    "3. Run YouTube/LinkedIn content push\n\n"
    "My recommendation:\n"
    "  Start with option 1 — closest to revenue with no upfront spend.\n\n"
    "Approval boundary:\n  I will not publish, email subscribers..."
)
update_conversation_state(
    user_message="how do we make money this week",
    hermes_response=meaningful_response,
    tool_used="money_strategy",
)

state2 = load_conversation_state()
r_ctx = handle_simplify_request("can you simplify your response", state2)
check("with-context simplify returns string", isinstance(r_ctx, str))
check("with-context simplify is non-empty", len(r_ctx.strip()) > 20)
check("with-context no evidence dump", "Live answer sources:" not in r_ctx)
check("with-context no quality fallback", "quality response" not in r_ctx.lower())
check("with-context not the no-prior-context message",
      "don't have a previous response to simplify yet" not in r_ctx.lower())

# ── process_with_cfo_brain for simplify ───────────────────────────────────────

r3 = process_with_cfo_brain("can you simplify your response", "can you simplify your response")
check("process: simplify returns string", isinstance(r3, str) and len(r3) > 10)
check("process: no evidence dump", "live answer sources:" not in (r3 or "").lower())
check("process: no quality fallback", "quality response" not in (r3 or "").lower())

# Print summary
print(f"\nPhase 7C simplify follow-up live: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
