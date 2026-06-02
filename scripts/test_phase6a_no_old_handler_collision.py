"""
test_phase6a_no_old_handler_collision.py
Tests: Phase 6A phrases do NOT route to old handlers (next_best_move,
business_opportunities, handoff_check, blocker_triage, show_blockers,
approval_queue, top_revenue_move_today, continue_while_out).
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_phase6a_no_old_handler_collision ===\n")

from hermes_command_router.intake import classify_intent

OLD_INTENTS = {
    "next_best_move", "business_opportunities", "handoff_check",
    "blocker_triage", "show_blockers", "approval_queue",
    "top_revenue_move_today", "continue_while_out",
}

PHASE6A_PHRASES = [
    ("run daily operating cycle",          "daily_operating_cycle"),
    ("what should i work on today",        "daily_operating_cycle"),
    ("what should we work on today",       "daily_operating_cycle"),
    ("what should i focus on today",       "daily_operating_cycle"),
    ("daily plan",                         "daily_operating_cycle"),
    ("todays nexus plan",                  "daily_operating_cycle"),
    ("what needs my approval",             "daily_approval_needed"),
    ("show approval queue",                "daily_approval_needed"),
    ("pending approvals",                  "daily_approval_needed"),
    ("approval needed",                    "daily_approval_needed"),
    ("continue while i am out",            "daily_continue_while_out"),
    ("keep working while i am out",        "daily_continue_while_out"),
    ("what can you do while i am gone",    "daily_continue_while_out"),
    ("show today's top revenue move",      "daily_top_revenue_move"),
    ("what can make money today",          "daily_top_revenue_move"),
    ("how do we make money today",         "daily_top_revenue_move"),
    ("top revenue move",                   "daily_top_revenue_move"),
    ("show today's blockers",              "daily_blockers"),
    ("show blockers",                      "daily_blockers"),
    ("what is blocked",                    "daily_blockers"),
    ("blockers today",                     "daily_blockers"),
    ("todays blockers",                    "daily_blockers"),
]

print("-- Phase 6A phrases do not route to old intents --")
for phrase, expected_intent in PHASE6A_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:50]}': intent not in OLD_INTENTS", intent not in OLD_INTENTS)

print("\n-- Phase 6A phrases route to correct new intents --")
for phrase, expected_intent in PHASE6A_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:50]}': intent == {expected_intent}", intent == expected_intent)

print("\n-- old intent names not in _PLAIN_INTENTS --")
from hermes_command_router.router import _PLAIN_INTENTS
check("'approval_queue' not in _PLAIN_INTENTS",      "approval_queue" not in _PLAIN_INTENTS)
check("'continue_while_out' not in _PLAIN_INTENTS",  "continue_while_out" not in _PLAIN_INTENTS)
check("'top_revenue_move_today' not in _PLAIN_INTENTS", "top_revenue_move_today" not in _PLAIN_INTENTS)
check("'show_blockers' not in _PLAIN_INTENTS",       "show_blockers" not in _PLAIN_INTENTS)

print("\n-- new intent names present in _PLAIN_INTENTS --")
check("'daily_approval_needed' in _PLAIN_INTENTS",    "daily_approval_needed" in _PLAIN_INTENTS)
check("'daily_continue_while_out' in _PLAIN_INTENTS", "daily_continue_while_out" in _PLAIN_INTENTS)
check("'daily_top_revenue_move' in _PLAIN_INTENTS",   "daily_top_revenue_move" in _PLAIN_INTENTS)
check("'daily_blockers' in _PLAIN_INTENTS",           "daily_blockers" in _PLAIN_INTENTS)
check("'daily_operating_cycle' in _PLAIN_INTENTS",    "daily_operating_cycle" in _PLAIN_INTENTS)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
