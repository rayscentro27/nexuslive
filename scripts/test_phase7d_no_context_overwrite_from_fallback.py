"""
test_phase7d_no_context_overwrite_from_fallback.py
Phase 7D: option maps, recommendations, and selected option text
are never overwritten by fallback/clarification/failure responses.
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
    mark_option_selected,
    load_conversation_state,
    get_option,
    get_task,
    get_active_recommendation,
    get_last_meaningful_response,
    get_selected_option_context,
)

# ── Seed strategic context ─────────────────────────────────────────────────────

strategic = (
    "WEEKLY MONEY PLAN\n\n"
    "1. Lead magnet funnel\n"
    "2. Membership launch\n"
    "3. Content push\n\n"
    "My recommendation:\n  Start with option 1.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state("how do we make money this week", strategic, tool_used="money_strategy")
mark_option_selected(1, text="Lead magnet funnel — connect to opt-in and affiliate offer")

state_seed = load_conversation_state()
check("seed: 3 options in map", len(state_seed.get("last_option_map", {})) == 3)
check("seed: active_recommendation set", bool(state_seed.get("active_recommendation")))
check("seed: selected_text set", bool(state_seed.get("last_selected_option_text")))

# ── Response types that must NOT overwrite strategic context ──────────────────

non_overwrite_responses = [
    ("PLAIN ANSWER\n\nI don't have task 1 from the last response.\nTry asking first.",
     "task-missing fallback"),
    ("PLAIN ANSWER\n\nI don't have the option list from the last response.\nPlease ask first.",
     "option-list-missing fallback"),
    ("PLAIN ANSWER\n\nI don't have a previous response to simplify yet.\nTry: 'how do we make money'.",
     "simplify no-context"),
    ("PLAIN ANSWER\n\nI don't have a recent recommendation to explain.\nTry asking first.",
     "explain no-context"),
    ("I NEED CLARIFICATION\n\nI understood your message but don't have enough context.",
     "clarification request"),
    ("CORRECTING COURSE\n\nI understand — logged as training example.\n\nApproval boundary:\n  I will not publish...",
     "failure learning"),
    ("CORRECTING COURSE\n\nI understand — that was not the right response.\n\nApproval boundary:\n  I will not publish...",
     "failure correction"),
]

for response_text, label in non_overwrite_responses:
    update_conversation_state(f"user message for {label}", response_text)
    s = load_conversation_state()

    check(f"{label}: option_map NOT erased",
          len(s.get("last_option_map", {})) == 3)
    check(f"{label}: active_recommendation NOT erased",
          bool(s.get("active_recommendation")))
    check(f"{label}: selected_option_text NOT erased",
          "lead magnet" in (s.get("last_selected_option_text") or "").lower())
    check(f"{label}: last_meaningful_response NOT overwritten to fallback text",
          "lead magnet" in (s.get("last_meaningful_response") or "").lower()
          or "money plan" in (s.get("last_meaningful_response") or "").lower()
          or "option selected" in (s.get("last_meaningful_response") or "").lower())

# ── Getters still work after all non-overwrite responses ─────────────────────

check("get_option(1) still works", "lead magnet" in (get_option(1) or "").lower() or get_option(1) is not None)
check("get_task(1) still works", get_task(1) is not None)
check("get_active_recommendation() still returns value", bool(get_active_recommendation()))
check("get_last_meaningful_response() still strategic",
      "lead magnet" in (get_last_meaningful_response() or "").lower()
      or "money plan" in (get_last_meaningful_response() or "").lower()
      or "option selected" in (get_last_meaningful_response() or "").lower())

sel_num, sel_text = get_selected_option_context()
check("get_selected_option_context() still returns (1, text)", sel_num == 1)
check("selected_text still mentions lead magnet", "lead magnet" in (sel_text or "").lower())

# ── Strategic response DOES update option map ─────────────────────────────────

new_strategic = (
    "NEXUS PLAN\n\n"
    "Tasks:\n1. Fix landing page\n2. Add CTA\n3. Set up email\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state("what are the tasks", new_strategic)
s_new = load_conversation_state()
check("new strategic response updates option_map", len(s_new.get("last_option_map", {})) == 3)
check("new option map has new content",
      "fix" in (s_new.get("last_option_map", {}).get("1") or "").lower()
      or "landing" in (s_new.get("last_option_map", {}).get("1") or "").lower())

print(f"\nPhase 7D no context overwrite from fallback: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
