"""
test_phase7d_active_recommendation_survives_followups.py
Phase 7D: active_recommendation persists through OPTION SELECTED, fallbacks, and
failure-learning responses so "EXPLAIN YOUR RECOMMENDATION" always uses the real one.
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


from lib.hermes_cfo_brain import handle_explain_request, process_with_cfo_brain
from lib.hermes_conversation_state import (
    update_conversation_state,
    mark_option_selected,
    get_active_recommendation,
    load_conversation_state,
)

# ── Seed: money strategy with explicit recommendation ─────────────────────────

money = (
    "WEEKLY MONEY PLAN\n\n"
    "1. Activate the funding readiness lead magnet funnel with an affiliate offer\n"
    "2. Launch Nexus membership at a founding-member price\n"
    "3. Run a YouTube/LinkedIn content push\n\n"
    "My recommendation:\n"
    "  Start with option 1 — it is closest to revenue with no upfront spend.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state("how do we make money this week", money, tool_used="money_strategy")
check("seed: active_recommendation set", bool(get_active_recommendation()))
check("seed: active_recommendation mentions option 1",
      "option 1" in (get_active_recommendation() or "").lower())

# ── Active recommendation survives OPTION SELECTED ───────────────────────────

option_selected = (
    "OPTION SELECTED\n\nYou chose option 1:\n  Activate the lead magnet funnel\n\n"
    "Approval boundary:\n  I will not publish..."
)
mark_option_selected(1, text="Activate the funding readiness lead magnet funnel with an affiliate offer")
update_conversation_state("lets do 1", option_selected, tool_used="option_selection")
check("active_rec survives OPTION SELECTED", bool(get_active_recommendation()))
check("active_rec still mentions option 1 after selection",
      "option 1" in (get_active_recommendation() or "").lower())

# ── Active recommendation survives fallback responses ────────────────────────

fallback = "PLAIN ANSWER\n\nI don't have task 1 from the last response.\nTry again."
update_conversation_state("what was task 1", fallback)
check("active_rec survives fallback", bool(get_active_recommendation()))
check("active_rec still correct after fallback",
      "option 1" in (get_active_recommendation() or "").lower())

# ── Active recommendation survives failure-learning ──────────────────────────

failure = "CORRECTING COURSE\n\nI understand — logged as training example.\n\nApproval boundary:\n  I will not publish..."
update_conversation_state("that is not what i meant", failure)
check("active_rec survives CORRECTING COURSE", bool(get_active_recommendation()))
from lib.hermes_conversation_state import _is_meaningful_strategic_response
check("CORRECTING COURSE does not overwrite last_meaningful_response (not strategic)",
      not _is_meaningful_strategic_response(failure))

# ── handle_explain_request uses active recommendation / selected option ────────

state = load_conversation_state()
r = handle_explain_request("explain your recommendation in plain language", state)

check("explain returns string", isinstance(r, str) and len(r) > 10)
check("explain has PLAIN ANSWER header", "PLAIN ANSWER" in r)
check("explain shows active recommendation context",
      "lead magnet" in r.lower() or "option 1" in r.lower() or "recommendation" in r.lower())
check("explain no evidence dump", "Live answer sources:" not in r)
check("explain no quality fallback", "quality response" not in r.lower())
check("explain no 'plain-language mode enabled'", "plain-language mode enabled" not in r.lower())
check("explain has approval boundary", "approval" in r.lower())

# ── process_with_cfo_brain for explain ───────────────────────────────────────

r2 = process_with_cfo_brain(
    "explain your recommendation in plain language",
    "explain your recommendation in plain language"
)
check("process: explain returns PLAIN ANSWER", "PLAIN ANSWER" in (r2 or ""))
check("process: explain uses active context",
      "lead magnet" in (r2 or "").lower() or "option" in (r2 or "").lower())
check("process: explain no evidence dump", "Live answer sources:" not in (r2 or ""))

# ── Multiple follow-ups don't lose recommendation ────────────────────────────

for _ in range(3):
    fb = "PLAIN ANSWER\n\nI don't have a previous response to simplify yet.\nTry asking first."
    update_conversation_state("can you simplify", fb)

check("active_rec survives 3 simplify fallbacks", bool(get_active_recommendation()))
r3 = handle_explain_request("explain your recommendation", load_conversation_state())
check("explain still works after 3 fallbacks",
      "PLAIN ANSWER" in r3 and "approval" in r3.lower())

print(f"\nPhase 7D active recommendation survives follow-ups: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
