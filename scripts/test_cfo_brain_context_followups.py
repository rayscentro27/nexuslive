"""
test_cfo_brain_context_followups.py
Phase 7B: CFO Brain — context follow-up threading.
Verifies that follow-up messages are classified correctly.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passes = 0
failures = 0

def check(label, cond):
    global passes, failures
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures += 1
    else:
        passes += 1
    print(f"  [{status}] {label}")
    return cond


from lib.hermes_cfo_brain import classify_cfo_intent, should_use_cfo_brain

print("\nCFO Brain Context Follow-up Tests")
print("=" * 50)

print("\n-- Follow-up classification --")
_FOLLOWUPS = [
    ("and what does that mean", "explain_previous_response"),
    ("what do you mean", "explain_previous_response"),
    ("what was that again", "followup_question"),
    ("can you repeat that", "followup_question"),
    ("what was task 1", "task_reference"),
    ("let's do 1", "option_selection"),
    ("ok let's do option 2", "option_selection"),
    ("explain that", "explain_previous_response"),
    ("simplify your response", "simplify_previous_response"),
]
for msg, expected in _FOLLOWUPS:
    intent = classify_cfo_intent(msg)
    check(f"'{msg}' → {expected}", intent == expected)

print("\n-- CFO brain activates for follow-ups --")
_NATURAL = [
    "and what does that mean",
    "what was task 1",
    "let's do 1",
    "explain your recommendation in plain language",
    "can you simplify your response",
]
for msg in _NATURAL:
    check(f"brain activates for: '{msg}'", should_use_cfo_brain(msg) is True)

print("\n-- Conversation state module available --")
try:
    from lib.hermes_conversation_state import (
        load_conversation_state,
        update_conversation_state,
        get_option,
        get_task,
        get_last_recommendation,
        get_last_response_full,
        has_active_context,
    )
    check("conversation state imports", True)
except Exception as e:
    check(f"conversation state imports: {e}", False)

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
