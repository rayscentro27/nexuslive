"""
test_learning_loop_bulk_approval_fast_response.py
Tests: approve_all_pending_lessons() completes quickly for small batches (≤5).
Also verifies _batch_update_proposals() exists and works.
"""
import sys, os, time
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


print("=== test_learning_loop_bulk_approval_fast_response ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import (
    create_lesson_proposal,
    approve_all_pending_lessons,
    _batch_update_proposals,
    list_pending_lessons,
    _load_proposals,
)

_tmp_dir = Path(tempfile.mkdtemp())
_orig_proposals = _ll.PROPOSALS_FILE

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    # ── _batch_update_proposals exists and works ──────────────────────────────
    print("-- _batch_update_proposals: basic behavior --")
    check("_batch_update_proposals is callable", callable(_batch_update_proposals))

    p1 = create_lesson_proposal("learn this: always verify before reporting status")
    p2 = create_lesson_proposal("learn this: log all knowledge gaps rather than guessing")

    updated = _batch_update_proposals({
        p1["lesson_id"]: {"proposed_status": "test_marked", "test_field": "abc"},
        p2["lesson_id"]: {"proposed_status": "test_marked", "test_field": "def"},
    })
    check("batch_update returns 2",  updated == 2)

    props = _load_proposals()
    p1_loaded = next((p for p in props if p["lesson_id"] == p1["lesson_id"]), None)
    p2_loaded = next((p for p in props if p["lesson_id"] == p2["lesson_id"]), None)
    check("p1 status updated",  p1_loaded and p1_loaded.get("proposed_status") == "test_marked")
    check("p2 status updated",  p2_loaded and p2_loaded.get("proposed_status") == "test_marked")
    check("p1 test_field set",  p1_loaded and p1_loaded.get("test_field") == "abc")

    # ── Empty batch returns 0 ─────────────────────────────────────────────────
    updated_empty = _batch_update_proposals({})
    check("empty batch returns 0", updated_empty == 0)

    # ── Unknown lesson_id: no crash, returns 0 ────────────────────────────────
    updated_missing = _batch_update_proposals({"nonexistent_id": {"proposed_status": "x"}})
    check("unknown lesson_id: no crash, returns 0", updated_missing == 0)

    # ── approve_all timing: ≤5 safe lessons finishes under 30s without Supabase ──
    print("\n-- approve_all timing: local validation path --")
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals2.jsonl"
    for msg in [
        "learn this: check evidence before answering status questions",
        "learn this: log gaps rather than inventing answers",
        "learn this: confirm artifact version before reporting",
    ]:
        create_lesson_proposal(msg)

    start = time.monotonic()
    result = approve_all_pending_lessons()
    elapsed = time.monotonic() - start

    check(f"completes in under 30s (took {elapsed:.2f}s)", elapsed < 30)
    check("reviewed == 3", result["reviewed"] == 3)
    check("error key present", "error" in result)
    check("approved_lessons is list", isinstance(result["approved_lessons"], list))
    check("blocked_lessons is list",  isinstance(result["blocked_lessons"],  list))
    check("skipped_lessons is list",  isinstance(result["skipped_lessons"],  list))
    check("count consistency",
          result["reviewed"] == result["approved"] + result["blocked"] + result["skipped"])

    # ── router fast response: ≤5 pending returns BULK LESSON APPROVAL (not STARTED) ──
    print("\n-- router: ≤5 pending returns BULK LESSON APPROVAL COMPLETE or BULK LESSON APPROVAL --")
    from hermes_command_router.router import run_command
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals3.jsonl"
    for msg in [
        "learn this: always use active artifacts for status answers",
        "learn this: summarize decision log before reporting",
    ]:
        create_lesson_proposal(msg)

    resp = run_command("approve all pending lessons", source="cli")
    check("response is non-empty",         bool(resp))
    check("contains BULK LESSON APPROVAL", "BULK LESSON APPROVAL" in resp)
    check("does NOT say STARTED (≤5)",     "BULK LESSON APPROVAL STARTED" not in resp)

finally:
    _ll.PROPOSALS_FILE = _orig_proposals
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
