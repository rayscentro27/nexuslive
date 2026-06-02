"""
test_daily_cycle_mark_complete_normalization.py
Tests: mark-complete prefix stripping handles colon, dash, and varied command forms.
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

DUMP_MARKERS = ["artifact_inventory", "═══", "HERMES REPORT", "handoff dump", "Executive Memory"]

ITEM_TEXT = "Review and score latest source intake records"


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


def seed():
    from lib.hermes_daily_cycle_state import save_daily_cycle_state
    save_daily_cycle_state({
        "date": "2026-06-02",
        "top_priority": "Finalize lead magnet",
        "blockers": [],
        "approval_items": [],
        "safe_next_actions": [
            ITEM_TEXT,
            "Update internal action queue with current status",
            "Research top content asset improvement opportunities",
            "Log any new knowledge gaps found during review",
        ],
        "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
    })


print("=== test_daily_cycle_mark_complete_normalization ===\n")

from hermes_command_router.router import run_command, _plain_mark_daily_item_complete
from lib.hermes_daily_cycle_state import list_pending_cycle_items, load_latest_daily_cycle_state

# ── prefix stripping logic (unit test) ───────────────────────────────────────
print("-- prefix stripping produces clean item title --")
COMMAND_FORMS = [
    f"mark item complete: {ITEM_TEXT}",
    f"mark item complete {ITEM_TEXT}",
    f"mark daily item complete: {ITEM_TEXT}",
    f"mark daily item complete {ITEM_TEXT}",
    f"complete daily item: {ITEM_TEXT}",
    f"complete item {ITEM_TEXT}",
    f"mark as complete: {ITEM_TEXT}",
    f"mark complete: {ITEM_TEXT}",
    f"mark done: {ITEM_TEXT}",
]
EXPECTED_FRAGMENT = "review and score"
for raw_cmd in COMMAND_FORMS:
    # Simulate the prefix-strip logic directly
    lowered = raw_cmd.strip().lower()
    for prefix in (
        "mark daily item complete",
        "mark daily item done",
        "complete daily item",
        "complete item",
        "mark as complete",
        "mark as done",
        "mark item complete",
        "mark item done",
        "mark complete",
        "mark done",
        "mark it complete",
        "mark it done",
        "that is complete",
        "mark that complete",
        "completed that",
        "finished that item",
    ):
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix):].strip()
            break
    lowered = lowered.lstrip(":–—-• \t")
    for suffix in (" as complete", " complete", " as done", " done"):
        if lowered.endswith(suffix):
            lowered = lowered[: -len(suffix)].strip()
            break
    check(f"stripped({repr(raw_cmd[:55])}) contains 'review and score'",
          EXPECTED_FRAGMENT in lowered)

# ── run_command marks item successfully ───────────────────────────────────────
print("\n-- run_command: mark with colon succeeds --")
seed()
resp = run_command(f"mark item complete: {ITEM_TEXT}", source="cli")
check("starts with DAILY ITEM MARKED COMPLETE", resp.startswith("DAILY ITEM MARKED COMPLETE"))
check("shows completed item text", ITEM_TEXT in resp or "review and score" in resp.lower())
check("no dump markers", no_dump(resp))
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("contains evidence line", "hermes_daily_cycle_state.json" in resp)

# ── item removed from pending after mark ─────────────────────────────────────
print("\n-- item no longer in pending after mark --")
pending = list_pending_cycle_items()
still_pending = any(ITEM_TEXT.lower() in p["item"].lower() for p in pending)
check("item removed from pending list", not still_pending)

# ── item recorded in completed_items ─────────────────────────────────────────
print("\n-- item recorded in completed_items --")
state = load_latest_daily_cycle_state()
completed = state.get("completed_items") or []
completed_labels = [c.get("item", "").lower() for c in completed]
check("item in completed_items", any(ITEM_TEXT.lower() in label for label in completed_labels))
check("completed_at present", any("completed_at" in c for c in completed))

# ── mark without colon also works ────────────────────────────────────────────
print("\n-- mark without colon also works --")
seed()
resp2 = run_command(f"mark item complete {ITEM_TEXT}", source="cli")
check("no-colon form → DAILY ITEM MARKED COMPLETE", resp2.startswith("DAILY ITEM MARKED COMPLETE"))
check("no-colon form shows completed item", ITEM_TEXT in resp2 or "review and score" in resp2.lower())

# ── daily item complete variant ───────────────────────────────────────────────
print("\n-- 'mark daily item complete' variant --")
seed()
resp3 = run_command(f"mark daily item complete: {ITEM_TEXT}", source="cli")
check("daily-variant → DAILY ITEM MARKED COMPLETE", resp3.startswith("DAILY ITEM MARKED COMPLETE"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
