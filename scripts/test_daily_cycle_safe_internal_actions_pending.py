"""
test_daily_cycle_safe_internal_actions_pending.py
Tests: safe_next_actions appear in pending items list and can be marked complete.
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


print("=== test_daily_cycle_safe_internal_actions_pending ===\n")

from lib.hermes_daily_cycle_state import (
    save_daily_cycle_state, list_pending_cycle_items,
    mark_cycle_item_completed, load_latest_daily_cycle_state,
)
from hermes_command_router.router import run_command

SAFE_ACTIONS = [
    "Review and score latest source intake records",
    "Update internal action queue with current status",
    "Research top content asset improvement opportunities",
    "Log any new knowledge gaps found during review",
]

save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "blockers": [{"blocker": "Open knowledge gaps: external_info_question",
                  "category": "knowledge", "fix": "Send sources"}],
    "approval_items": [],
    "safe_next_actions": SAFE_ACTIONS,
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

# ── safe_next_actions appear as safe_action type in pending ───────────────────
print("-- safe_next_actions appear in list_pending_cycle_items --")
pending = list_pending_cycle_items()
types = {p["type"] for p in pending}
check("'safe_action' type present in pending", "safe_action" in types)
safe_in_pending = [p for p in pending if p["type"] == "safe_action"]
check(f"all 4 safe actions present ({len(safe_in_pending)})", len(safe_in_pending) == 4)
for action in SAFE_ACTIONS:
    found = any(action.lower() in p["item"].lower() for p in safe_in_pending)
    check(f"'{action[:50]}' in pending", found)

# ── PENDING DAILY ITEMS response shows safe internal items section ─────────────
print("\n-- PENDING DAILY ITEMS response includes safe internal items --")
resp = run_command("show pending items", source="cli")
check("starts with PENDING DAILY ITEMS", resp.startswith("PENDING DAILY ITEMS"))
check("shows 'Safe internal items' section", "Safe internal items" in resp)
check("shows 'Review and score' in response",
      "Review and score" in resp)
check("shows 'Update internal action queue' in response",
      "Update internal action queue" in resp)

# ── safe action can be marked complete ───────────────────────────────────────
print("\n-- mark safe action complete --")
result = mark_cycle_item_completed("Review and score latest source intake records")
check("mark success == True", result.get("success") == True)
check("matched item text present", "Review and score" in result.get("message", ""))

# ── after marking, safe action removed from pending ──────────────────────────
print("\n-- after mark: safe action removed from pending --")
pending_after = list_pending_cycle_items()
still_in_pending = any("Review and score" in p["item"] for p in pending_after)
check("item removed from pending", not still_in_pending)
check("other safe actions still present", len([p for p in pending_after if p["type"] == "safe_action"]) == 3)

# ── completed safe action recorded in state ───────────────────────────────────
print("\n-- completed safe action in completed_items --")
state = load_latest_daily_cycle_state()
completed = state.get("completed_items") or []
check("completed_items has 1 entry", len(completed) == 1)
check("completed entry is the safe action",
      "Review and score" in (completed[0].get("item") or ""))
check("_source_list == safe_next_actions",
      completed[0].get("_source_list") == "safe_next_actions")

# ── safe action excluded from pending after reload ───────────────────────────
print("\n-- completed safe action excluded on reload --")
pending_reload = list_pending_cycle_items()
still_there = any("Review and score" in p["item"] for p in pending_reload)
check("item stays excluded after reload", not still_there)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
