"""
test_learning_loop_source_traceability.py
Tests: explain_lesson_source and get_last_lesson_proposal for full traceability.
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


print("=== test_learning_loop_source_traceability ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import (
    create_lesson_proposal,
    explain_lesson_source,
    get_last_lesson_proposal,
)

_tmp_dir = Path(tempfile.mkdtemp())

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    # ── get_last_lesson_proposal: empty state ─────────────────────────────────
    print("-- get_last_lesson_proposal: empty state --")
    last_empty = get_last_lesson_proposal()
    check("returns None when no proposals", last_empty is None)

    # ── create a proposal and verify traceability ─────────────────────────────
    print("\n-- explain_lesson_source: from local proposals --")
    p1 = create_lesson_proposal(
        "record this lesson: always check the artifact registry before reporting",
        context={"summary": "traceability test"},
    )
    lid = p1["lesson_id"]

    info = explain_lesson_source(lid)
    check("info has memory_id",     info.get("memory_id") == lid)
    check("info has title",         bool(info.get("title")))
    check("info has status",        bool(info.get("status")))
    check("info has source",        "Ray" in info.get("source", ""))
    check("info has source_hash",   bool(info.get("source_hash")))
    check("info has created_at",    bool(info.get("created_at")))
    check("info has proposal_file", bool(info.get("proposal_file")))

    # ── No secrets in traceability output ─────────────────────────────────────
    print("\n-- explain_lesson_source: no secrets in output --")
    import json
    info_str = json.dumps(info)
    SECRET_PATTERNS = ["eyJ", "sk-", "sbp_", "service_role"]
    for pat in SECRET_PATTERNS:
        check(f"no secret pattern {pat!r} in traceability", pat not in info_str)

    # ── get_last_lesson_proposal returns most recent ───────────────────────────
    print("\n-- get_last_lesson_proposal: returns most recent --")
    p2 = create_lesson_proposal(
        "learn this: log every knowledge gap for future improvement"
    )
    last = get_last_lesson_proposal()
    check("get_last returns a proposal", last is not None)
    check("get_last returns p2 (most recent)",
          last is not None and last.get("lesson_id") == p2["lesson_id"])

    # ── explain_lesson_source: not_found case ─────────────────────────────────
    print("\n-- explain_lesson_source: not_found case --")
    info_nf = explain_lesson_source("lesson_doesnotexist_xyz")
    check("not_found status",     info_nf.get("status") == "not_found")
    check("not_found memory_id",  info_nf.get("memory_id") == "lesson_doesnotexist_xyz")

    # ── router: 'where did that lesson come from' returns LESSON SOURCE ────────
    print("\n-- router: lesson_source response --")
    from hermes_command_router.router import run_command
    resp = run_command("where did that lesson come from", source="cli")
    check("lesson_source: non-empty", bool(resp))
    check("lesson_source: LESSON SOURCE header", "LESSON SOURCE" in resp)
    check("lesson_source: no evidence dump", "artifact_inventory" not in resp)
    check("lesson_source: mentions Telegram", "Telegram" in resp)
    check("lesson_source: mentions proposal file", "hermes_lesson_proposals" in resp)

finally:
    _ll.PROPOSALS_FILE = _ll.PROPOSALS_FILE.__class__(_ll._ROOT / "docs" / "reports" / "memory" / "learning" / "hermes_lesson_proposals.jsonl")
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
