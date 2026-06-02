"""
test_learning_loop_bulk_approval_timeout_prevention.py
Tests: batch path structure; ≤5 → sync, >5 → STARTED + background thread.
"""
import sys, os
from pathlib import Path
import tempfile, shutil, inspect

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


print("=== test_learning_loop_bulk_approval_timeout_prevention ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import (
    create_lesson_proposal,
    approve_all_pending_lessons,
    _batch_update_proposals,
    _update_proposal,
    list_pending_lessons,
    _load_proposals,
)

_tmp_dir = Path(tempfile.mkdtemp())
_orig_proposals = _ll.PROPOSALS_FILE

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    # ── approve_all_pending_lessons source uses _batch_update_proposals ───────
    print("-- approve_all_pending_lessons uses _batch_update_proposals --")
    src = inspect.getsource(approve_all_pending_lessons)
    check("uses _batch_update_proposals", "_batch_update_proposals" in src)
    check("does NOT call _update_proposal in main path",
          src.count("_update_proposal(") == 0)

    # ── batch path: blocked lessons written via _batch_update_proposals ───────
    print("\n-- batch path: JSONL rewrite count for 3 lessons --")
    write_count = [0]
    orig_batch_update = _ll._batch_update_proposals

    def counting_batch_update(updates):
        write_count[0] += 1
        return orig_batch_update(updates)

    _ll._batch_update_proposals = counting_batch_update

    for msg in [
        "learn this: check evidence before answering",
        "learn this: log gaps instead of guessing",
        "learn this: ask Ray before publishing content",
    ]:
        create_lesson_proposal(msg)

    result = approve_all_pending_lessons()
    check("batch update called at most once for JSONL", write_count[0] <= 1)
    check("count consistency",
          result["reviewed"] == result["approved"] + result["blocked"] + result["skipped"])
    _ll._batch_update_proposals = orig_batch_update

    # ── router: >5 pending returns BULK LESSON APPROVAL STARTED ──────────────
    print("\n-- router: >5 pending → BULK LESSON APPROVAL STARTED --")
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals2.jsonl"

    safe_msgs = [
        "learn this: always check the decision log before reporting",
        "learn this: log all knowledge gaps before guessing",
        "learn this: check action queue for pending items",
        "learn this: use hermes_memory_v2 for active lessons",
        "learn this: summarize context before giving status",
        "learn this: confirm artifact version before reporting it",
    ]
    for msg in safe_msgs:
        create_lesson_proposal(msg)

    pending = list_pending_lessons(limit=100)
    check(f"6 pending set up (got {len(pending)})", len(pending) == 6)

    from hermes_command_router.router import run_command
    resp = run_command("approve all pending lessons", source="cli")
    check("response non-empty",                    bool(resp))
    check("returns BULK LESSON APPROVAL STARTED",  "BULK LESSON APPROVAL STARTED" in resp)
    check("mentions background processing",        "background" in resp.lower())
    check("mentions hermes_memory_v2",             "hermes_memory_v2" in resp)
    check("no evidence dump markers",
          not any(m in resp for m in ["artifact_inventory", "handoff dump", "═══", "HERMES REPORT"]))

    # ── No old table writes anywhere in approve_all_pending_lessons ───────────
    print("\n-- no old table writes --")
    OLD_TABLES = ["ai_memory", "hermes_executive_memory", "knowledge_items", "nexus_skills"]
    for tbl in OLD_TABLES:
        check(f"no old table {tbl!r} in batch path",
              f'"{tbl}"' not in src and f"'{tbl}'" not in src)

finally:
    _ll.PROPOSALS_FILE = _orig_proposals
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
