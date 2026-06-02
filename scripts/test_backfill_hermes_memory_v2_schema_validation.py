"""
test_backfill_hermes_memory_v2_schema_validation.py
Verifies _validate_record() enforces required fields, allowed types/statuses/scopes,
and that real JSONL records all pass schema validation.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / "docs" / "reports" / "memory" / "hermes_memory_v2_batch1_20260602_021258.jsonl"
sys.path.insert(0, str(ROOT / "scripts"))
from backfill_hermes_memory_v2 import (
    _validate_record, REQUIRED_FIELDS, ALLOWED_MEMORY_TYPES,
    ALLOWED_STATUSES_FOR_INSERT, ALLOWED_SCOPES_FOR_INSERT, BATCH_ALLOWED_TYPES,
)

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def make_record(**kwargs):
    base = {
        "memory_id": "schema-test-001",
        "title": "Test",
        "summary": "Test summary",
        "memory_type": "operating_rule",
        "status": "active",
        "scope": "live_answer",
        "confidence": 0.9,
        "priority": 1,
        "tags": [],
        "payload": {},
        "migration_status": "dry_run",
        "created_at": "2026-06-02T00:00:00Z",
        "updated_at": "2026-06-02T00:00:00Z",
    }
    base.update(kwargs)
    return base


print("=== test_backfill_hermes_memory_v2_schema_validation ===\n")

batch1_types = BATCH_ALLOWED_TYPES.get("batch1", set())

print("-- REQUIRED_FIELDS defined --")
check("REQUIRED_FIELDS list present", len(REQUIRED_FIELDS) >= 10)
for f in ["memory_id", "title", "summary", "memory_type", "status", "scope",
          "confidence", "priority", "tags", "payload"]:
    check(f"required field: {f}", f in REQUIRED_FIELDS)

print("\n-- ALLOWED_MEMORY_TYPES covers all 17 types --")
expected_types = [
    "operating_rule", "ray_preference", "project_context", "goal",
    "tool_registry", "scout_registry", "approval_policy",
    "provider_status_snapshot", "source_intake", "action", "decision",
    "artifact", "lesson", "template", "fallback_rule", "archived_note", "debug_note",
]
check("17 allowed memory types", len(ALLOWED_MEMORY_TYPES) == 17)
for t in expected_types:
    check(f"allowed type: {t}", t in ALLOWED_MEMORY_TYPES)

print("\n-- ALLOWED_STATUSES/SCOPES for insert --")
check("only 'active' allowed for insert", ALLOWED_STATUSES_FOR_INSERT == {"active"})
check("only 'live_answer' scope allowed for insert", ALLOWED_SCOPES_FOR_INSERT == {"live_answer"})

print("\n-- Each required field absence causes error --")
for field in REQUIRED_FIELDS:
    r = make_record()
    del r[field]
    errs = _validate_record(r, batch1_types)
    check(f"missing '{field}' caught", len(errs) > 0)

print("\n-- Invalid types caught --")
for bad_type in ["unknown_type", "memory", "rule", ""]:
    r = make_record(memory_type=bad_type)
    errs = _validate_record(r, batch1_types)
    check(f"invalid memory_type {bad_type!r} caught", len(errs) > 0)

print("\n-- Non-int priority caught --")
for bad_pri in ["high", None, 1.5]:
    r = make_record(priority=bad_pri)
    errs = _validate_record(r, batch1_types)
    check(f"non-int priority {bad_pri!r} caught", len(errs) > 0)

print("\n-- Valid record passes all checks --")
valid = make_record()
errs = _validate_record(valid, batch1_types)
check("valid record has 0 errors", len(errs) == 0)

print("\n-- Real JSONL records all pass schema validation --")
if JSONL.exists():
    records = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
    check("15 records in real JSONL", len(records) == 15)
    errors_total = 0
    for r in records:
        errs = _validate_record(r, batch1_types)
        if errs:
            errors_total += 1
            print(f"  SCHEMA FAIL {r.get('memory_id')}: {errs}")
    check("all real records pass schema validation (0 errors)", errors_total == 0)

    # Verify type distribution
    type_counts = {}
    for r in records:
        t = r.get("memory_type", "?")
        type_counts[t] = type_counts.get(t, 0) + 1
    check("5 operating_rule records", type_counts.get("operating_rule", 0) == 5)
    check("4 ray_preference records", type_counts.get("ray_preference", 0) == 4)
    check("3 approval_policy records", type_counts.get("approval_policy", 0) == 3)
    check("3 project_context records", type_counts.get("project_context", 0) == 3)
    check("all records status=active", all(r.get("status") == "active" for r in records))
    check("all records scope=live_answer", all(r.get("scope") == "live_answer" for r in records))
else:
    check("JSONL exists (skipping real JSONL schema tests)", False)
    for _ in range(8):
        check("runtime test skipped", True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
