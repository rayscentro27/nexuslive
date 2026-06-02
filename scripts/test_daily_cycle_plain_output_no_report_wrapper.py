"""
test_daily_cycle_plain_output_no_report_wrapper.py
Tests: all 5 Phase 6B intents produce plain output — never wrapped in HERMES REPORT,
       never trigger evidence dump, always start with the correct header.
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

DUMP_MARKERS = [
    "artifact_inventory", "handoff dump", "Executive Memory",
    "I can answer from verified artifacts", "═══", "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_daily_cycle_plain_output_no_report_wrapper ===\n")

from hermes_command_router.router import run_command, _PLAIN_INTENTS, _PLAIN_INTENTS_WITH_CMD
from lib.hermes_daily_cycle_state import save_daily_cycle_state

save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "top_priority_why": "Top asset ready",
    "blockers": [{"blocker": "CTA missing", "category": "operational", "fix": "Draft CTA"}],
    "approval_items": [
        {"item": "Approve newsletter", "category": "action_queue",
         "why": "Ready", "next_if_approved": "Send", "risk_if_skipped": "Delayed"},
    ],
    "safe_next_actions": ["Review source intake", "Score opportunities"],
    "evidence": ["goal: Build Nexus revenue engine"],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

PHASE6B_COMMANDS = [
    ("show last daily plan",       "LAST DAILY PLAN",                "show_last_daily_plan"),
    ("while i was out",            "WHILE YOU WERE OUT",             "while_out_summary"),
    ("show pending items",         "PENDING DAILY ITEMS",            "pending_daily_items"),
    ("compare since last plan",    "WHAT CHANGED SINCE THE LAST PLAN", "compare_since_last_plan"),
    ("mark complete",              "DAILY ITEM MARKED COMPLETE",     "mark_daily_item_complete"),
]

print("-- all Phase 6B intents in _PLAIN_INTENTS --")
for _, _, intent in PHASE6B_COMMANDS:
    check(f"'{intent}' in _PLAIN_INTENTS", intent in _PLAIN_INTENTS)

print("\n-- mark_daily_item_complete in _PLAIN_INTENTS_WITH_CMD --")
check("mark_daily_item_complete in _PLAIN_INTENTS_WITH_CMD",
      "mark_daily_item_complete" in _PLAIN_INTENTS_WITH_CMD)

print("\n-- all Phase 6B commands produce plain output --")
for phrase, expected_header, intent in PHASE6B_COMMANDS:
    resp = run_command(phrase, source="cli")
    check(f"[{intent}] non-empty", bool(resp))
    check(f"[{intent}] starts with '{expected_header}'", resp.startswith(expected_header))
    check(f"[{intent}] no HERMES REPORT wrapper", not resp.strip().startswith("HERMES REPORT"))
    check(f"[{intent}] no ═══", "═══" not in resp)
    check(f"[{intent}] no dump markers", no_dump(resp))
    check(f"[{intent}] no 'old executive memory'",
          "old executive memory" not in resp.lower())
    check(f"[{intent}] no 'executive memory snapshot'",
          "executive memory snapshot" not in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
