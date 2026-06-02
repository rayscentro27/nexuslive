"""
test_learning_loop_bulk_approval.py
Tests: approve_all_pending_lessons() behavior — approves safe lessons, skips duplicates, returns counts.
"""
import sys, os
from pathlib import Path
import tempfile, shutil

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


print("=== test_learning_loop_bulk_approval ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import (
    create_lesson_proposal,
    approve_all_pending_lessons,
    list_pending_lessons,
)

_tmp_dir = Path(tempfile.mkdtemp())
_orig_proposals = _ll.PROPOSALS_FILE

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    # ── Empty state ───────────────────────────────────────────────────────────
    print("-- approve_all_pending_lessons: empty state --")
    result = approve_all_pending_lessons()
    check("empty: reviewed=0",  result["reviewed"] == 0)
    check("empty: approved=0",  result["approved"] == 0)
    check("empty: blocked=0",   result["blocked"] == 0)
    check("empty: skipped=0",   result["skipped"] == 0)
    check("empty: error=None",  result["error"] is None)

    # ── All safe: all approved ────────────────────────────────────────────────
    print("\n-- approve_all_pending_lessons: 3 safe lessons --")
    safe_lessons = [
        "learn this: always check the latest artifact before reporting status",
        "learn this: log knowledge gaps instead of guessing",
        "learn this: ask Ray before publishing any content",
    ]
    for msg in safe_lessons:
        create_lesson_proposal(msg)

    result = approve_all_pending_lessons()
    check("reviewed == 3",   result["reviewed"] == 3)
    check("approved == 3",   result["approved"] == 3)
    check("blocked == 0",    result["blocked"] == 0)
    check("skipped == 0",    result["skipped"] == 0)
    check("approved_lessons is list", isinstance(result["approved_lessons"], list))
    check("3 approved_lessons entries", len(result["approved_lessons"]) == 3)
    for lsn in result["approved_lessons"]:
        check(f"lesson {lsn['lesson_id'][:15]} has title", bool(lsn.get("title")))

    # ── Already approved: skipped as duplicate ────────────────────────────────
    print("\n-- approve_all_pending_lessons: already approved → skipped --")
    # Create a new lesson and manually mark as approved
    p_dup = create_lesson_proposal("learn this: check memory v2 before answering")
    _ll._update_proposal(p_dup["lesson_id"], {
        "proposed_status": "approved",
        "approved_at": "2026-06-02T10:00:00+00:00",
        "approved_by": "Ray Davis",
    })
    # Now the pending list is empty (we approved all 3 above, and p_dup is already approved)
    result2 = approve_all_pending_lessons()
    check("no pending after bulk approval", result2["reviewed"] == 0)

    # ── Limit parameter ───────────────────────────────────────────────────────
    print("\n-- approve_all_pending_lessons: limit=2 from 4 pending --")
    for msg in [
        "learn this: summarize current context before giving status",
        "learn this: use decision log as a source",
        "learn this: check action queue before recommending next steps",
        "learn this: show knowledge gaps instead of guessing",
    ]:
        create_lesson_proposal(msg)
    pending_before = list_pending_lessons(limit=100)
    check("4 pending before limited approval", len(pending_before) == 4)

    result3 = approve_all_pending_lessons(limit=2)
    check("limited: reviewed == 2",     result3["reviewed"] == 2)
    check("limited: approved <= 2",     result3["approved"] <= 2)
    pending_after = list_pending_lessons(limit=100)
    check("2 still pending after limit=2",  len(pending_after) == 2)

    # ── Return structure ──────────────────────────────────────────────────────
    print("\n-- approve_all_pending_lessons: return structure --")
    result4 = approve_all_pending_lessons()
    check("result has 'reviewed' key",         "reviewed" in result4)
    check("result has 'approved' key",         "approved" in result4)
    check("result has 'blocked' key",          "blocked" in result4)
    check("result has 'skipped' key",          "skipped" in result4)
    check("result has 'approved_lessons' key", "approved_lessons" in result4)
    check("result has 'blocked_lessons' key",  "blocked_lessons" in result4)
    check("result has 'skipped_lessons' key",  "skipped_lessons" in result4)
    check("result has 'error' key",            "error" in result4)

    # ── No old table writes ────────────────────────────────────────────────────
    print("\n-- approve_all_pending_lessons: no old table writes --")
    import inspect
    src = inspect.getsource(approve_all_pending_lessons)
    OLD_TABLES = ["ai_memory", "hermes_executive_memory", "knowledge_items", "nexus_skills"]
    for tbl in OLD_TABLES:
        check(f"no old table {tbl!r}", f'"{tbl}"' not in src and f"'{tbl}'" not in src)

finally:
    _ll.PROPOSALS_FILE = _orig_proposals
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
