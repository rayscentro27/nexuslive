"""
test_phase7c_no_old_fallbacks.py
Phase 7C tests: known failing messages do NOT produce evidence dumps or quality fallbacks.
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


from lib.hermes_cfo_brain import process_with_cfo_brain
from lib.hermes_conversation_state import update_conversation_state

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "artifact_inventory",
    "handoff_state",
    "HERMES REPORT",
    "intelligence_division",
]
GENERIC_FALLBACK_MARKERS = [
    "i wasn't able to generate",
    "quality response",
    "based on what i have available",
    "plain-language mode enabled",
    "plain language mode enabled",
    "i wasn't fully sure",
]


def has_evidence_dump(text: str) -> bool:
    return any(m in (text or "") for m in EVIDENCE_DUMP_MARKERS)


def has_generic_fallback(text: str) -> bool:
    return any(m in (text or "").lower() for m in GENERIC_FALLBACK_MARKERS)


# Seed meaningful state for follow-up tests
seed_response = (
    "WEEKLY MONEY PLAN\n\n"
    "1. Activate lead magnet funnel\n"
    "2. Launch Nexus membership\n"
    "3. Run content push\n\n"
    "My recommendation: Start with option 1.\n\n"
    "Approval boundary:\n  I will not publish..."
)
update_conversation_state(
    user_message="how do we make money this week",
    hermes_response=seed_response,
    tool_used="money_strategy",
)

# ── All Phase 7C failing messages produce no evidence dump ───────────────────

critical_messages = [
    ("how do we make money this week",           "how do we make money this week"),
    ("lets do 1",                                "lets do 1"),
    ("what was task 1",                          "what was task 1"),
    ("can you simplify your response",           "can you simplify your response"),
    ("explain your recommendation in plain language", "explain your recommendation in plain language"),
    ("what did you do this morning",             "what did you do this morning"),
    ("that is not what i meant",                 "that is not what i meant"),
]

for raw, norm in critical_messages:
    r = process_with_cfo_brain(raw, norm)
    check(f"'{raw[:40]}' → returns string", isinstance(r, str) and len(r) > 10)
    check(f"'{raw[:40]}' → no evidence dump", not has_evidence_dump(r or ""))
    check(f"'{raw[:40]}' → no quality fallback", not has_generic_fallback(r or ""))

# ── Responses have expected structure ────────────────────────────────────────

r_money = process_with_cfo_brain("how do we make money this week", "how do we make money this week")
check("money strategy has WEEKLY MONEY PLAN", "WEEKLY MONEY PLAN" in (r_money or ""))
check("money strategy has numbered options", any(f"{i}." in (r_money or "") for i in range(1, 4)))

r_option = process_with_cfo_brain("lets do 1", "lets do 1")
check("option selection has OPTION SELECTED", "OPTION SELECTED" in (r_option or ""))

r_task = process_with_cfo_brain("what was task 1", "what was task 1")
check("task ref has PLAIN ANSWER", "PLAIN ANSWER" in (r_task or ""))

r_morning = process_with_cfo_brain("what did you do this morning", "what did you do this morning")
check("morning has MORNING SUMMARY", "MORNING SUMMARY" in (r_morning or ""))

r_failure = process_with_cfo_brain("that is not what i meant", "that is not what i meant")
check("failure feedback has CORRECTING COURSE", "CORRECTING COURSE" in (r_failure or ""))

# ── All responses include approval boundary ───────────────────────────────────

for raw, norm in critical_messages:
    r = process_with_cfo_brain(raw, norm)
    check(f"'{raw[:35]}' has approval boundary",
          "approval" in (r or "").lower() or "will not publish" in (r or "").lower())

# Print summary
print(f"\nPhase 7C no old fallbacks: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
