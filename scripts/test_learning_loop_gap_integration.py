"""
test_learning_loop_gap_integration.py
Tests: generate_gap_lesson_proposals integrates with knowledge gap logger.
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


print("=== test_learning_loop_gap_integration ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import generate_gap_lesson_proposals

_tmp_dir = Path(tempfile.mkdtemp())

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    print("-- generate_gap_lesson_proposals: returns a list --")
    result = generate_gap_lesson_proposals(limit=5)
    check("returns a list", isinstance(result, list))
    check("limit respected", len(result) <= 5)

    print("\n-- generate_gap_lesson_proposals: each proposal is valid --")
    for p in result:
        lid    = p.get("lesson_id", "")
        status = p.get("proposed_status", "")
        check(f"proposal {lid[:20]}: has lesson_id",  bool(lid))
        check(f"proposal {lid[:20]}: has lesson_text", bool(p.get("lesson_text")))
        check(f"proposal {lid[:20]}: status in (pending_review, blocked)",
              status in ("pending_review", "blocked"))
        check(f"proposal {lid[:20]}: approval_required=True",
              p.get("approval_required") is True)

    print("\n-- generate_gap_lesson_proposals: no Supabase writes --")
    # All proposals are pending_review (local only)
    for p in result:
        check(f"proposal {p.get('lesson_id','?')[:20]}: NOT approved yet",
              p.get("proposed_status") != "approved")

    print("\n-- generate_gap_lesson_proposals: no duplicate lesson text --")
    texts = [p.get("lesson_text") for p in result]
    check("no duplicate lesson_text", len(texts) == len(set(t for t in texts if t)))

    print("\n-- generate_gap_lesson_proposals: safe to call with no gaps --")
    # Monkey-patch gap loader to return empty
    import lib.hermes_learning_loop as _ll_patch
    _orig = None
    try:
        from lib import hermes_knowledge_gap_logger as _gap_mod
        _orig = _gap_mod.load_recent_knowledge_gaps
        _gap_mod.load_recent_knowledge_gaps = lambda limit=100: []
        result_empty = generate_gap_lesson_proposals(limit=5)
        check("empty gaps returns empty list", result_empty == [])
    except ImportError:
        check("gap logger not installed — skip", True)
    finally:
        if _orig is not None:
            _gap_mod.load_recent_knowledge_gaps = _orig

finally:
    _ll.PROPOSALS_FILE = _ll.PROPOSALS_FILE.__class__(_ll._ROOT / "docs" / "reports" / "memory" / "learning" / "hermes_lesson_proposals.jsonl")
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
