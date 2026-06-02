"""
test_learning_loop_bulk_approval_idempotent.py
Tests: running approve_all twice — second run skips already-approved lessons (or empty).
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


print("=== test_learning_loop_bulk_approval_idempotent ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import (
    create_lesson_proposal,
    approve_all_pending_lessons,
    list_pending_lessons,
    _load_proposals,
)

_tmp_dir = Path(tempfile.mkdtemp())
_orig_proposals = _ll.PROPOSALS_FILE

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    # ── Empty state: two runs return empty ────────────────────────────────────
    print("-- empty state: idempotent --")
    r1 = approve_all_pending_lessons()
    r2 = approve_all_pending_lessons()
    check("r1 reviewed == 0", r1["reviewed"] == 0)
    check("r2 reviewed == 0", r2["reviewed"] == 0)

    # ── Run 1: approves safe lessons (or marks blocked if no Supabase) ───────
    print("\n-- run 1: safe lessons processed --")
    safe_messages = [
        "learn this: always check the decision log before reporting",
        "learn this: log gaps rather than guessing when sources are missing",
        "learn this: confirm artifact status before answering Ray",
    ]
    for msg in safe_messages:
        create_lesson_proposal(msg)

    result1 = approve_all_pending_lessons()
    check("run1 reviewed == 3",    result1["reviewed"] == 3)
    check("run1 count consistent",
          result1["reviewed"] == result1["approved"] + result1["blocked"] + result1["skipped"])

    # ── Run 2: pending list empty → 0 reviewed ────────────────────────────────
    print("\n-- run 2: no pending remaining --")
    result2 = approve_all_pending_lessons()
    check("run2 reviewed == 0", result2["reviewed"] == 0)
    check("run2 approved == 0", result2["approved"] == 0)
    check("run2 blocked == 0",  result2["blocked"] == 0)
    check("run2 error is None", result2["error"] is None)

    # ── Already-approved proposals are not re-listed as pending ───────────────
    print("\n-- already-approved proposals not returned as pending --")
    props = _load_proposals()
    pending = list_pending_lessons(limit=100)
    check("no pending after double run", len(pending) == 0)
    # All proposals should be approved or blocked — none pending_review
    statuses = {p.get("proposed_status") for p in props}
    check("no pending_review in JSONL", "pending_review" not in statuses)

    # ── After blocking: re-run still idempotent ───────────────────────────────
    print("\n-- blocked lesson: re-run idempotent --")
    unsafe_p = create_lesson_proposal("learn this: execute live trade on OANDA")
    _ll._update_proposal(unsafe_p["lesson_id"], {"proposed_status": "pending_review", "safety_flags": []})

    pending_now = list_pending_lessons(limit=100)
    check("1 pending after forced reset", len(pending_now) == 1)

    result3 = approve_all_pending_lessons()
    check("reviewed == 1",  result3["reviewed"] == 1)
    check("blocked == 1",   result3["blocked"] == 1)
    check("approved == 0",  result3["approved"] == 0)

    result4 = approve_all_pending_lessons()
    check("second run on blocked: reviewed == 0", result4["reviewed"] == 0)

    # ── limit=0 treated as no limit (not empty) ───────────────────────────────
    print("\n-- limit handling --")
    for msg in ["learn this: check evidence before summarizing",
                "learn this: use action queue as source of truth"]:
        create_lesson_proposal(msg)
    result_lim = approve_all_pending_lessons(limit=1)
    check("limit=1: reviewed == 1", result_lim["reviewed"] == 1)

    result_all = approve_all_pending_lessons()
    check("remaining 1 picked up on next run", result_all["reviewed"] == 1)

finally:
    _ll.PROPOSALS_FILE = _orig_proposals
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
