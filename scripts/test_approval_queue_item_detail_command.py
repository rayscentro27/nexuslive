"""
test_approval_queue_item_detail_command.py
Tests: show_approval_item intent routing and APPROVAL ITEM N response.
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

DUMP_MARKERS = ["artifact_inventory", "═══", "HERMES REPORT", "handoff dump", "Executive Memory"]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_approval_queue_item_detail_command ===\n")

from lib.hermes_approval_queue import (
    _STATE_FILE, _save_state, normalize_approval_item,
)
from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

# ── seed one item ──────────────────────────────────────────────────────────────
raw = {
    "_source_type": "daily_cycle",
    "title": "Approve newsletter draft",
    "summary": "Newsletter ready to review",
    "category": "subscriber_email",
    "source": "daily_cycle_state",
    "source_path": "docs/reports/operations/hermes_daily_cycle_state.json",
    "related_action_id": "nl_draft_001",
    "risk_level": "high",
    "approval_required_for": "Newsletter must be approved before sending.",
    "if_approved": "Newsletter enters review queue.",
    "if_rejected": "Newsletter stays in draft.",
    "safe_internal_next_step": "Review newsletter draft.",
    "evidence_paths": ["docs/reports/operations/hermes_daily_cycle_state.json"],
    "created_at": "2026-06-02T10:00:00+00:00",
}
item = normalize_approval_item(raw, index=1)
state = {"created_at": "2026-06-02T10:00:00+00:00", "items": [item], "archived": []}
_save_state(state)

# ── routing ───────────────────────────────────────────────────────────────────
print("-- classify_intent routes to show_approval_item --")
DETAIL_PHRASES = [
    "show approval item 1",
    "approval item detail 1",
    "tell me about approval item 1",
    "details for approval item 1",
    "explain approval item 1",
]
for phrase in DETAIL_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"[{phrase[:50]}] → show_approval_item", intent == "show_approval_item")

# ── APPROVAL ITEM response format ─────────────────────────────────────────────
print("\n-- APPROVAL ITEM N response format --")
resp = run_command("show approval item 1", source="cli")
check("starts with APPROVAL ITEM", resp.startswith("APPROVAL ITEM"))
check("contains item title", "Approve newsletter draft" in resp or "newsletter" in resp.lower())
check("contains category", "subscriber" in resp.lower() or "email" in resp.lower())
check("contains risk", "high" in resp.lower() or "Risk:" in resp)
check("contains if approved", "If approved" in resp or "if approved" in resp.lower())
check("contains if rejected", "If rejected" in resp or "if rejected" in resp.lower())
check("contains approval boundary", "approval" in resp.lower() and "boundary" in resp.lower())
check("no dump markers", no_dump(resp))
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))

# ── non-existent item returns graceful message ────────────────────────────────
print("\n-- non-existent item ref --")
resp999 = run_command("show approval item 999", source="cli")
check("starts with APPROVAL ITEM", resp999.startswith("APPROVAL ITEM"))
check("not found message", "not found" in resp999.lower() or "no approval item" in resp999.lower())
check("no dump markers", no_dump(resp999))

# ── no item number → prompt ───────────────────────────────────────────────────
print("\n-- no item number --")
resp_bare = run_command("show approval item", source="cli")
check("starts with APPROVAL ITEM", resp_bare.startswith("APPROVAL ITEM"))
check("asks for item number", "number" in resp_bare.lower() or "specify" in resp_bare.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
