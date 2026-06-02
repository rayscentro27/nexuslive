"""
test_approval_queue_state_persistence.py
Tests: state file saves/loads correctly, history JSONL appends, approved/rejected preserved.
"""
import sys, os, json
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


print("=== test_approval_queue_state_persistence ===\n")

from lib.hermes_approval_queue import (
    _STATE_FILE, _HISTORY_FILE, _load_state, _save_state, _append_history,
    build_approval_queue, approve_approval_item, reject_approval_item,
    normalize_approval_item, _stable_id,
)

# ── seed test item ─────────────────────────────────────────────────────────────
raw = {
    "_source_type": "test",
    "title": "State persistence test item",
    "summary": "Testing save and load",
    "category": "internal_review",
    "source": "test",
    "source_path": "docs/test",
    "related_action_id": "persist_test_001",
    "risk_level": "low",
    "approval_required_for": "Test.",
    "if_approved": "Test proceeds.",
    "if_rejected": "Test cancelled.",
    "safe_internal_next_step": "Decide.",
    "evidence_paths": [],
    "created_at": "2026-06-02T10:00:00+00:00",
}
item = normalize_approval_item(raw, index=1)
state = {"created_at": "2026-06-02T10:00:00+00:00", "items": [item], "archived": []}
_save_state(state)

# ── state file exists and is valid JSON ───────────────────────────────────────
print("-- state file save/load --")
check("state file exists", _STATE_FILE.exists())
loaded = _load_state()
check("loaded items list", isinstance(loaded.get("items"), list))
check("item count == 1", len(loaded["items"]) == 1)
check("item approval_id preserved", loaded["items"][0].get("approval_id") == item["approval_id"])
check("item status preserved", loaded["items"][0].get("status") == "pending")

# ── history file appends ──────────────────────────────────────────────────────
print("\n-- history file append --")
before_lines = len(_HISTORY_FILE.read_text().splitlines()) if _HISTORY_FILE.exists() else 0
_append_history({"event": "test_entry", "approval_id": item["approval_id"], "timestamp": "2026-06-02T10:00:00+00:00"})
after_lines = len(_HISTORY_FILE.read_text().splitlines())
check("history file grew by 1", after_lines == before_lines + 1)
last_line = _HISTORY_FILE.read_text().splitlines()[-1]
last_entry = json.loads(last_line)
check("last entry has event", last_entry.get("event") == "test_entry")

# ── state file is valid JSON (no secrets) ─────────────────────────────────────
print("\n-- state file no secrets --")
state_text = _STATE_FILE.read_text()
state_data = json.loads(state_text)
check("_raw field not in saved item", "_raw" not in json.dumps(state_data))
check("approval_boundary in item", any("approval_boundary" in str(i) for i in state_data.get("items", [])))

# ── approved status persists across reload ───────────────────────────────────
print("\n-- approved status preserved on reload --")
# Manually set approved in state
for s_item in state_data["items"]:
    if s_item["approval_id"] == item["approval_id"]:
        s_item["status"] = "approved"
        s_item["ray_decision"] = "approved"
_save_state(state_data)

reloaded = _load_state()
saved_item = next((i for i in reloaded["items"] if i["approval_id"] == item["approval_id"]), {})
check("status==approved after reload", saved_item.get("status") == "approved")
check("ray_decision==approved after reload", saved_item.get("ray_decision") == "approved")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
