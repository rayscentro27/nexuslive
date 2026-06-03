"""
test_phase7c_universal_response_state_capture.py
Phase 7C tests: conversation state captures numbered items from ALL response types.
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
    _extract_numbered_list,
    _extract_recommendation,
)

# ── _extract_numbered_list parses all formats ─────────────────────────────────

plain_numbered = "Some header\n\n1. First option\n2. Second option\n3. Third option"
result = _extract_numbered_list(plain_numbered)
check("plain numbered: 3 items", len(result) == 3)
check("plain numbered: item 1", result.get(1) == "First option")
check("plain numbered: item 2", result.get(2) == "Second option")

bullet_prefixed = "Some header\n\n* 1. Option A\n* 2. Option B\n- 3. Option C"
result2 = _extract_numbered_list(bullet_prefixed)
check("bullet-prefixed: 3 items", len(result2) == 3)
check("bullet-prefixed: item 1", result2.get(1) == "Option A")
check("bullet-prefixed: item 2", result2.get(2) == "Option B")

option_format = "Header\n\nOption 1: Do the lead magnet\nOption 2: Launch membership"
result3 = _extract_numbered_list(option_format)
check("option format: 2 items", len(result3) == 2)
check("option format: item 1", "lead magnet" in (result3.get(1) or ""))

task_format = "Tasks:\nTask 1: Research competitors\nTask 2: Build landing page"
result4 = _extract_numbered_list(task_format)
check("task format: 2 items", len(result4) == 2)
check("task format: item 1", "competitor" in (result4.get(1) or ""))

empty_text = ""
result5 = _extract_numbered_list(empty_text)
check("empty text: returns empty dict", result5 == {})

# ── _extract_recommendation identifies recommendation correctly ───────────────

rec_text = "WEEKLY MONEY PLAN\n\n1. Do lead magnet\n2. Launch membership\n\nMy recommendation:\n  Start with option 1 — closest to revenue."
rec = _extract_recommendation(rec_text)
check("explicit 'My recommendation:' extracted", rec is not None)
check("recommendation not footer text", "approval" not in (rec or "").lower()[:30])

no_explicit_rec = "PLAIN ANSWER\n\n1. First task\n2. Second task\n\nApproval boundary: I will not publish"
rec2 = _extract_recommendation(no_explicit_rec)
check("fallback to first numbered item", rec2 == "First task")

# ── update_conversation_state saves numbered items ────────────────────────────

sample_response = (
    "WEEKLY MONEY PLAN\n\n"
    "Revenue readiness score: 72/100\n\n"
    "Best money moves this week:\n\n"
    "1. Activate the lead magnet funnel\n"
    "2. Launch Nexus membership\n"
    "3. Run YouTube content push\n\n"
    "My recommendation:\n"
    "  Start with option 1 — closest to revenue.\n\n"
    "Approval boundary:\n"
    "  I will not publish, email subscribers..."
)

state = update_conversation_state(
    user_message="how do we make money this week",
    hermes_response=sample_response,
    tool_used="money_strategy",
)

check("state saved option_map", bool(state.get("last_option_map")))
check("state option_map has 3 items", len(state.get("last_option_map", {})) == 3)
check("state option 1 is lead magnet", "lead magnet" in (state.get("last_option_map", {}).get("1") or "").lower())
check("state option 2 is membership", "membership" in (state.get("last_option_map", {}).get("2") or "").lower())
check("state has recommendation", bool(state.get("last_recommendation")))
check("state topic set", state.get("current_topic") is not None)
check("state updated_at set", bool(state.get("updated_at")))

# ── get_option and get_task resolve after state save ─────────────────────────

opt1 = get_option(1)
check("get_option(1) resolves after save", opt1 is not None)
check("get_option(1) is lead magnet", "lead magnet" in (opt1 or "").lower())

opt2 = get_option(2)
check("get_option(2) resolves", opt2 is not None)

task1 = get_task(1)
check("get_task(1) resolves after save", task1 is not None)

rec = get_last_recommendation()
check("get_last_recommendation returns non-empty", bool(rec))
check("recommendation not footer", "approval" not in (rec or "").lower()[:30])

# Print summary
print(f"\nPhase 7C universal response state capture: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
