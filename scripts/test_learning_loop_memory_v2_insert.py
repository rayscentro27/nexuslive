"""
test_learning_loop_memory_v2_insert.py
Tests: build_lesson_memory_v2_record produces valid hermes_memory_v2 schema.
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


print("=== test_learning_loop_memory_v2_insert ===\n")

import lib.hermes_learning_loop as _ll
from lib.hermes_learning_loop import (
    create_lesson_proposal,
    build_lesson_memory_v2_record,
    LESSON_TYPE,
    STATUS_ACTIVE,
    SCOPE_LIVE,
)

_tmp_dir = Path(tempfile.mkdtemp())

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    proposal = create_lesson_proposal(
        "record this lesson: prioritize current artifacts over stale memory",
        context={
            "summary":      "test context",
            "artifact_id":  "art_test_123",
            "action_id":    "action_test_456",
            "decision_id":  "dec_test_789",
            "source_id":    "src_test_abc",
        },
    )

    now = "2026-06-02T12:00:00+00:00"
    record = build_lesson_memory_v2_record({
        **proposal,
        "approved_at": now,
        "approved_by": "Ray Davis",
    })

    print("-- Required hermes_memory_v2 fields --")
    check("memory_id present",            bool(record.get("memory_id")))
    check("title present",                bool(record.get("title")))
    check("summary present",              bool(record.get("summary")))
    check("memory_type == lesson",        record.get("memory_type") == LESSON_TYPE)
    check("status == active",             record.get("status") == STATUS_ACTIVE)
    check("scope == live_answer",         record.get("scope") == SCOPE_LIVE)
    check("confidence present",           isinstance(record.get("confidence"), (int, float)))
    check("priority present",             isinstance(record.get("priority"), (int, float)))
    check("tags is a list",               isinstance(record.get("tags"), list))
    check("migration_status == approved",  record.get("migration_status") == "approved")
    check("migration_notes present",       bool(record.get("migration_notes")))
    check("payload is dict",               isinstance(record.get("payload"), dict))
    check("source == operator",            record.get("source") == "operator")
    check("created_at present",           bool(record.get("created_at")))
    check("updated_at present",           bool(record.get("updated_at")))

    print("\n-- Payload fields --")
    payload = record.get("payload", {})
    check("payload.lesson_text present",         bool(payload.get("lesson_text")))
    check("payload.source_message_hash present", bool(payload.get("source_message_hash")))
    check("payload.source_context present",      bool(payload.get("source_context")))
    check("payload.approved_by = Ray Davis",     payload.get("approved_by") == "Ray Davis")
    check("payload.approved_at present",         bool(payload.get("approved_at")))

    print("\n-- Related IDs (top-level columns) --")
    check("related_artifact_id at top level",   record.get("related_artifact_id") == "art_test_123")
    check("related_action_id at top level",     record.get("related_action_id") == "action_test_456")
    check("related_decision_id at top level",   record.get("related_decision_id") == "dec_test_789")
    check("related_source_id at top level",     record.get("related_source_id") == "src_test_abc")

    print("\n-- No secrets in record --")
    import json
    record_str = json.dumps(record)
    SECRET_PATTERNS = [
        "eyJ",           # JWT
        "sk-",           # OpenAI key
        "sbp_",          # Supabase personal
        "service_role",
        "anon_key",
    ]
    for pat in SECRET_PATTERNS:
        check(f"no {pat!r} in record", pat not in record_str)

    print("\n-- memory_id matches lesson_id --")
    check("memory_id == lesson_id", record["memory_id"] == proposal["lesson_id"])

    print("\n-- tags include ray_lesson --")
    check("tags include ray_lesson", "ray_lesson" in record.get("tags", []))

finally:
    _ll.PROPOSALS_FILE = _ll.PROPOSALS_FILE.__class__(_ll._ROOT / "docs" / "reports" / "memory" / "learning" / "hermes_lesson_proposals.jsonl")
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
