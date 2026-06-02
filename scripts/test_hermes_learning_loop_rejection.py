"""
test_hermes_learning_loop_rejection.py
Tests: reject_lesson — local JSONL update, no Supabase writes.
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


print("=== test_hermes_learning_loop_rejection ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import (
    create_lesson_proposal,
    reject_lesson,
    list_pending_lessons,
    list_rejected_lessons,
)

_tmp_dir = Path(tempfile.mkdtemp())
_orig_proposals = _ll.PROPOSALS_FILE

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    # ── reject_lesson: not_found ──────────────────────────────────────────────
    print("-- reject_lesson: not_found --")
    result = reject_lesson("lesson_doesnotexist999")
    check("not_found returns ok=False", not result.get("ok"))
    check("not_found status field", result.get("status") == "not_found")

    # ── reject_lesson: happy path ─────────────────────────────────────────────
    print("\n-- reject_lesson: happy path --")
    proposal = create_lesson_proposal(
        "learn this: always verify memory before reporting to Ray"
    )
    lid = proposal["lesson_id"]
    check("proposal starts as pending", proposal.get("proposed_status") == "pending_review")
    check("proposal in pending list",
          any(p["lesson_id"] == lid for p in list_pending_lessons()))

    result = reject_lesson(lid, reason="test rejection — not needed")
    check("reject returns ok=True", result.get("ok") is True)
    check("reject status=rejected", result.get("status") == "rejected")
    check("reject lesson_id matches", result.get("lesson_id") == lid)

    # Verify it's no longer in pending
    pending_after = list_pending_lessons()
    check("rejected lesson not in pending list",
          not any(p["lesson_id"] == lid for p in pending_after))

    # Verify it's in rejected list
    rejected = list_rejected_lessons()
    matched = next((p for p in rejected if p["lesson_id"] == lid), None)
    check("rejected lesson appears in rejected list", matched is not None)
    if matched:
        check("rejected_reason recorded", bool(matched.get("rejected_reason")))
        check("rejected_at recorded", bool(matched.get("rejected_at")))
        check("proposed_status=rejected", matched.get("proposed_status") == "rejected")

    # ── reject_lesson: no Supabase interaction ────────────────────────────────
    print("\n-- reject_lesson: no Supabase write --")
    import inspect
    src_reject = inspect.getsource(reject_lesson)
    check("reject_lesson has no supabase client call",
          "create_client" not in src_reject)

    # ── Double rejection is idempotent ────────────────────────────────────────
    print("\n-- reject_lesson: double rejection is safe --")
    result2 = reject_lesson(lid)
    check("second reject returns ok=True (found, rewrites)", result2.get("ok") is True)

finally:
    _ll.PROPOSALS_FILE = _orig_proposals
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
