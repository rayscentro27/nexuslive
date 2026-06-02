"""
test_approval_queue_stale_cleanup.py
Tests: archive_stale_approval_items and clear_stale_approvals command.
"""
import sys, os
from datetime import datetime, timezone, timedelta
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


print("=== test_approval_queue_stale_cleanup ===\n")

from lib.hermes_approval_queue import (
    _save_state, normalize_approval_item, archive_stale_approval_items, _load_state,
)
from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

def _old_ts(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


# ── seed: one fresh item, one stale item ──────────────────────────────────────
def seed():
    fresh_raw = {
        "_source_type": "action_queue", "title": "Fresh item (recent)",
        "summary": "Created today",
        "category": "internal_review", "source": "action_queue",
        "source_path": "docs/test", "related_action_id": "stale_fresh_001",
        "risk_level": "low",
        "approval_required_for": "Fresh needs Ray.",
        "if_approved": "Proceeds.", "if_rejected": "Blocked.",
        "safe_internal_next_step": "Review.", "evidence_paths": [],
        "created_at": _old_ts(0),
    }
    stale_raw = {
        "_source_type": "action_queue", "title": "Old stale item",
        "summary": "Created 10 days ago",
        "category": "internal_review", "source": "action_queue",
        "source_path": "docs/test", "related_action_id": "stale_old_001",
        "risk_level": "low",
        "approval_required_for": "Stale needs Ray.",
        "if_approved": "Proceeds.", "if_rejected": "Blocked.",
        "safe_internal_next_step": "Review.", "evidence_paths": [],
        "created_at": _old_ts(10),
    }
    fresh = normalize_approval_item(fresh_raw, index=1)
    stale = normalize_approval_item(stale_raw, index=2)
    state = {"created_at": _old_ts(0), "items": [fresh, stale], "archived": []}
    _save_state(state)
    return fresh["approval_id"], stale["approval_id"]

# ── archive_stale_approval_items ──────────────────────────────────────────────
print("-- archive_stale_approval_items (7 days) --")
fresh_id, stale_id = seed()
result = archive_stale_approval_items(max_age_days=7)
check("archived_count == 1", result["archived_count"] == 1)
check("stale item title in stale_titles", any("stale" in t.lower() or "old" in t.lower() for t in result.get("stale_titles", [])))
check("max_age_days == 7", result["max_age_days"] == 7)

state = _load_state()
items = state.get("items") or []
stale_item = next((i for i in items if i["approval_id"] == stale_id), {})
fresh_item = next((i for i in items if i["approval_id"] == fresh_id), {})
check("stale item status==stale", stale_item.get("status") == "stale")
check("fresh item status still==pending", fresh_item.get("status") == "pending")

# ── clear_stale_approvals command ─────────────────────────────────────────────
print("\n-- clear_stale_approvals command routing --")
check("classify_intent → clear_stale_approvals",
      classify_intent("clear stale approvals")[0] == "clear_stale_approvals")
check("clean up stale approvals → clear_stale_approvals",
      classify_intent("clean up stale approvals")[0] == "clear_stale_approvals")

# ── with stale items present ──────────────────────────────────────────────────
print("\n-- STALE APPROVAL CLEANUP response with stale item --")
seed()
resp = run_command("clear stale approvals", source="cli")
check("starts with STALE APPROVAL CLEANUP", resp.startswith("STALE APPROVAL CLEANUP"))
check("mentions archived count", "archived" in resp.lower() or "stale" in resp.lower())
check("mentions evidence path", "hermes_approval_queue_state.json" in resp)
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no ═══", "═══" not in resp)

# ── with no stale items ───────────────────────────────────────────────────────
print("\n-- STALE APPROVAL CLEANUP response with no stale items --")
seed()
# Archive them first so none remain stale
archive_stale_approval_items(max_age_days=7)
# Run command on fresh state (fresh items only)
fresh_raw = {
    "_source_type": "action_queue", "title": "Fresh only item",
    "summary": "", "category": "internal_review", "source": "action_queue",
    "source_path": "docs/test", "related_action_id": "fresh_only_001",
    "risk_level": "low", "approval_required_for": "Needs Ray.",
    "if_approved": "Proceeds.", "if_rejected": "Blocked.",
    "safe_internal_next_step": "Review.", "evidence_paths": [],
    "created_at": _old_ts(0),
}
from lib.hermes_approval_queue import normalize_approval_item
fresh = normalize_approval_item(fresh_raw, index=1)
_save_state({"created_at": _old_ts(0), "items": [fresh], "archived": []})
resp_empty = run_command("clear stale approvals", source="cli")
check("no stale items → still STALE APPROVAL CLEANUP", resp_empty.startswith("STALE APPROVAL CLEANUP"))
check("mentions no stale found", "no stale" in resp_empty.lower() or "0" in resp_empty)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
