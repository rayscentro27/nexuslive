"""
test_cfo_brain_no_unsafe_actions.py
Phase 7B: CFO Brain — no unsafe actions.
Verifies that all CFO brain responses include the approval
boundary and do not trigger unsafe actions.
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


from lib.hermes_cfo_brain import (
    handle_simplify_request, handle_explain_request, handle_option_selection,
    handle_task_reference, handle_morning_activity, handle_queue_status,
    handle_money_strategy, handle_failure_feedback,
    handle_prompt_generation_request, handle_recommendation_question,
    _SAFETY_BOUNDARY,
)

UNSAFE_ACTION_MARKERS = [
    "email sent",
    "published to",
    "deployed to",
    "money transferred",
    "stripe activated",
    "live trading started",
    "affiliate program applied",
    "supabase write",
    "subscribed users",
    "payment processed",
]

APPROVAL_REQUIRED = "explicit ray approval"

print("\nCFO Brain No Unsafe Actions Tests")
print("=" * 50)

print("\n-- Safety boundary constant --")
check("safety boundary not empty", len(_SAFETY_BOUNDARY) > 20)
check("mentions Ray approval", "Ray approval" in _SAFETY_BOUNDARY)
check("mentions no publishing", "publish" in _SAFETY_BOUNDARY.lower())
check("mentions no email", "email" in _SAFETY_BOUNDARY.lower())
check("mentions no spending", "spend" in _SAFETY_BOUNDARY.lower() or "money" in _SAFETY_BOUNDARY.lower())
check("mentions no live trading", "live trading" in _SAFETY_BOUNDARY.lower())
check("mentions no Stripe", "stripe" in _SAFETY_BOUNDARY.lower())

print("\n-- All handlers include approval boundary --")
_HANDLERS = [
    ("handle_simplify_request", handle_simplify_request, "can you simplify"),
    ("handle_explain_request", handle_explain_request, "explain that"),
    ("handle_option_selection", handle_option_selection, "let's do 1"),
    ("handle_task_reference", handle_task_reference, "what was task 1"),
    ("handle_queue_status", handle_queue_status, "what tasks are pending"),
    ("handle_failure_feedback", handle_failure_feedback, "that is not what i meant"),
    ("handle_recommendation_question", handle_recommendation_question, "what do you recommend"),
]
for name, handler, msg in _HANDLERS:
    resp = handler(msg, {})
    check(f"{name} — has approval boundary",
          APPROVAL_REQUIRED in (resp or "").lower())
    for marker in UNSAFE_ACTION_MARKERS:
        check(f"{name} — no unsafe: {marker!r}", marker not in (resp or "").lower())

print("\n-- Prompt generation includes safety block --")
r = handle_prompt_generation_request("create a prompt for claude to fix this", {})
check("prompt gen — not None", r is not None)
check("prompt gen — includes safety language",
      "ray approval" in (r or "").lower() or "safety" in (r or "").lower() or
      "i will not" in (r or "").lower())

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
