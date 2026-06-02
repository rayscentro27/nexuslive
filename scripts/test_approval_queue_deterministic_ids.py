"""
test_approval_queue_deterministic_ids.py
Tests: stable approval_id is deterministic, dedup works, merge preserves status.
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


print("=== test_approval_queue_deterministic_ids ===\n")

from lib.hermes_approval_queue import (
    _stable_id, normalize_approval_item, _save_state, _load_state,
    build_approval_queue, approve_approval_item,
)
from lib.hermes_daily_cycle_state import save_daily_cycle_state

# ── _stable_id is deterministic ───────────────────────────────────────────────
print("-- _stable_id determinism --")
aid1 = _stable_id("action_queue:act_001")
aid2 = _stable_id("action_queue:act_001")
aid3 = _stable_id("action_queue:act_002")
check("same input → same id", aid1 == aid2)
check("different input → different id", aid1 != aid3)
check("format: starts with apq_", aid1.startswith("apq_"))
check("length: apq_ + 10 chars", len(aid1) == 14)

# ── normalize_approval_item stable id ────────────────────────────────────────
print("\n-- normalize_approval_item stable id --")
raw = {
    "_source_type": "action_queue", "title": "Test determinism",
    "summary": "", "category": "internal_review", "source": "action_queue",
    "source_path": "docs/test", "related_action_id": "determ_001",
    "risk_level": "low", "approval_required_for": "Test.",
    "if_approved": "Proceeds.", "if_rejected": "Blocked.",
    "safe_internal_next_step": "Review.", "evidence_paths": [],
    "created_at": "2026-06-02T10:00:00+00:00",
}
i1 = normalize_approval_item(raw, index=1)
i2 = normalize_approval_item(raw, index=1)
check("same raw → same approval_id", i1["approval_id"] == i2["approval_id"])
i3 = normalize_approval_item({**raw, "related_action_id": "determ_002"}, index=1)
check("different action_id → different approval_id", i1["approval_id"] != i3["approval_id"])

# ── build_approval_queue deduplicates ─────────────────────────────────────────
print("\n-- build_approval_queue deduplicates same id --")
item = normalize_approval_item(raw, index=1)
item["status"] = "pending"
dup  = normalize_approval_item(raw, index=2)
dup["status"] = "pending"
_save_state({"created_at": "2026-06-02T10:00:00+00:00", "items": [item, dup], "archived": []})

# Build from seeded daily cycle state (should add fresh items but not dup)
save_daily_cycle_state({
    "date": "2026-06-02", "top_priority": "Test",
    "blockers": [], "approval_items": [], "safe_next_actions": [],
    "memory_v2_count": 0, "goals_count": 0, "action_count": 0,
})
items = build_approval_queue()
ids = [i["approval_id"] for i in items]
check("no duplicate approval_ids", len(ids) == len(set(ids)))

# ── approved status preserved across rebuild ──────────────────────────────────
print("\n-- approved status preserved across rebuild --")
# Seed a single item, approve it, then rebuild
save_daily_cycle_state({
    "date": "2026-06-02", "top_priority": "Test",
    "blockers": [], "approval_items": [
        {"item": "Test approval preservation",
         "category": "internal_review",
         "why": "Test.", "next_if_approved": "Proceed.", "risk_if_skipped": "None."},
    ], "safe_next_actions": [],
    "memory_v2_count": 0, "goals_count": 0, "action_count": 0,
})
first_build = build_approval_queue()
if first_build:
    fid = first_build[0]["approval_id"]
    approve_approval_item(1)

    # Rebuild — should preserve approved status
    second_build = build_approval_queue()
    preserved = next((i for i in second_build if i["approval_id"] == fid), None)
    if preserved:
        check("approved status preserved after rebuild",
              preserved.get("status") == "approved")
    else:
        check("item present after rebuild", False)
else:
    check("first build returned items", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
