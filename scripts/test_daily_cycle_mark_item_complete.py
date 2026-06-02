"""
test_daily_cycle_mark_item_complete.py
Tests: mark_cycle_item_completed moves items from pending to completed_items.
       mark_daily_item_complete intent routes and returns DAILY ITEM MARKED COMPLETE.
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

DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory", "═══", "HERMES REPORT"]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_daily_cycle_mark_item_complete ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS
from lib.hermes_daily_cycle_state import (
    save_daily_cycle_state, mark_cycle_item_completed,
    load_latest_daily_cycle_state, list_pending_cycle_items,
)


def _seed_state():
    save_daily_cycle_state({
        "date": "2026-06-02",
        "top_priority": "Finalize lead magnet",
        "blockers": [
            {"blocker": "CTA not drafted", "category": "operational", "fix": "Draft CTA"},
            {"blocker": "Lead magnet missing intro", "category": "operational", "fix": "Write intro"},
        ],
        "approval_items": [
            {"item": "Approve newsletter draft", "category": "action_queue",
             "why": "Ready to send", "next_if_approved": "Send", "risk_if_skipped": "Delayed"},
        ],
        "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
    })


# ── mark_cycle_item_completed — successful match ──────────────────────────────
print("-- mark_cycle_item_completed: successful match --")
_seed_state()
result = mark_cycle_item_completed("newsletter")
check("success == True", result.get("success") == True)
check("message contains 'Marked complete'", "Marked complete" in result.get("message", ""))
check("completed_item is a dict", isinstance(result.get("completed_item"), dict))

state_after = load_latest_daily_cycle_state()
completed = state_after.get("completed_items") or []
check("completed_items has 1 entry", len(completed) == 1)
check("completed entry has completed_at", "completed_at" in completed[0])
check("completed entry has _source_list", "_source_list" in completed[0])
remaining_pending = list_pending_cycle_items()
check("item removed from pending", all("newsletter" not in str(p).lower() for p in remaining_pending))

# ── mark_cycle_item_completed — no match ─────────────────────────────────────
print("\n-- mark_cycle_item_completed: no match --")
_seed_state()
result_miss = mark_cycle_item_completed("nonexistent item XYZ")
check("success == False on no match", result_miss.get("success") == False)
check("message mentions no match", "no pending item matched" in result_miss.get("message", "").lower())

# ── mark_cycle_item_completed — no state ─────────────────────────────────────
print("\n-- mark_cycle_item_completed: no state --")
from lib.hermes_daily_cycle_state import _OP_STATE_FILE
import shutil
backup = _OP_STATE_FILE.with_suffix(".bak")
if _OP_STATE_FILE.exists():
    shutil.copy(_OP_STATE_FILE, backup)
    _OP_STATE_FILE.unlink()
result_no_state = mark_cycle_item_completed("anything")
check("success == False when no state", result_no_state.get("success") == False)
if backup.exists():
    shutil.copy(backup, _OP_STATE_FILE)
    backup.unlink()

# ── intent in _PLAIN_INTENTS ──────────────────────────────────────────────────
print("\n-- mark_daily_item_complete in _PLAIN_INTENTS --")
check("mark_daily_item_complete in _PLAIN_INTENTS", "mark_daily_item_complete" in _PLAIN_INTENTS)

# ── phrase classification ─────────────────────────────────────────────────────
print("\n-- phrase classification --")
PHRASES = [
    "mark complete",
    "mark as complete",
    "mark done",
    "mark it complete",
    "mark item complete",
    "that is complete",
    "mark that complete",
]
for phrase in PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:50])}) == mark_daily_item_complete",
          intent == "mark_daily_item_complete")

# ── response structure ────────────────────────────────────────────────────────
print("\n-- run_command response structure --")
_seed_state()
resp = run_command("mark complete", source="cli")
check("non-empty", bool(resp))
check("starts with DAILY ITEM MARKED COMPLETE",
      resp.startswith("DAILY ITEM MARKED COMPLETE"))
check("no dump markers", no_dump(resp))
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no ═══", "═══" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
