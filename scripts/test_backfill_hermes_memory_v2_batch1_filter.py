"""
test_backfill_hermes_memory_v2_batch1_filter.py
Verifies load_and_filter() behavior for Batch 1:
- Only operating_rule, ray_preference, approval_policy, project_context pass
- Other types are excluded
- Limit is enforced
- status=active required
- scope=live_answer required
"""
import sys, json, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from backfill_hermes_memory_v2 import load_and_filter, _validate_record, BATCH_ALLOWED_TYPES

JSONL = ROOT / "docs" / "reports" / "memory" / "hermes_memory_v2_batch1_20260602_021258.jsonl"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def make_record(**kwargs):
    base = {
        "memory_id": "test-001",
        "title": "Test record",
        "summary": "A test record",
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


print("=== test_backfill_hermes_memory_v2_batch1_filter ===\n")

print("-- Batch 1 allowed types --")
batch1_types = BATCH_ALLOWED_TYPES.get("batch1", set())
check("batch1 allows operating_rule", "operating_rule" in batch1_types)
check("batch1 allows ray_preference", "ray_preference" in batch1_types)
check("batch1 allows approval_policy", "approval_policy" in batch1_types)
check("batch1 allows project_context", "project_context" in batch1_types)
check("batch1 does NOT allow provider_status_snapshot", "provider_status_snapshot" not in batch1_types)
check("batch1 does NOT allow fallback_rule", "fallback_rule" not in batch1_types)
check("batch1 does NOT allow source_intake", "source_intake" not in batch1_types)

print("\n-- _validate_record: valid record passes --")
valid = make_record()
errs = _validate_record(valid, batch1_types)
check("valid record: 0 errors", len(errs) == 0)

print("\n-- _validate_record: wrong type excluded --")
bad_type = make_record(memory_type="provider_status_snapshot")
errs_bt = _validate_record(bad_type, batch1_types)
check("provider_status_snapshot excluded from batch1", len(errs_bt) > 0)
check("error mentions memory_type", any("memory_type" in e for e in errs_bt))

print("\n-- _validate_record: wrong status excluded --")
bad_status = make_record(status="archived")
errs_bs = _validate_record(bad_status, batch1_types)
check("archived status excluded", len(errs_bs) > 0)
check("error mentions status", any("status" in e for e in errs_bs))

print("\n-- _validate_record: wrong scope excluded --")
bad_scope = make_record(scope="historical")
errs_sc = _validate_record(bad_scope, batch1_types)
check("historical scope excluded", len(errs_sc) > 0)
check("error mentions scope", any("scope" in e for e in errs_sc))

print("\n-- _validate_record: missing required field --")
missing_field = make_record()
del missing_field["summary"]
errs_mf = _validate_record(missing_field, batch1_types)
check("missing 'summary' field causes error", len(errs_mf) > 0)
check("error mentions missing fields", any("missing" in e for e in errs_mf))

print("\n-- load_and_filter: real JSONL --")
if JSONL.exists():
    selected, excluded, all_records = load_and_filter(JSONL, "batch1", 15, batch1_types)
    check("all 15 records loaded from real JSONL", len(all_records) == 15)
    check("all 15 records selected (0 excluded)", len(selected) == 15)
    check("excluded count is 0", len(excluded) == 0)
    check("all selected are operating_rule/ray_preference/approval_policy/project_context",
          all(r["memory_type"] in batch1_types for r in selected))
    check("all selected have status=active", all(r.get("status") == "active" for r in selected))
    check("all selected have scope=live_answer", all(r.get("scope") == "live_answer" for r in selected))

    # Test limit enforcement
    selected5, _, _ = load_and_filter(JSONL, "batch1", 5, batch1_types)
    check("limit=5 returns at most 5 records", len(selected5) <= 5)
else:
    check("JSONL exists (skipping runtime filter tests)", False)
    for _ in range(8):
        check("runtime test skipped", True)

print("\n-- load_and_filter: synthetic JSONL with mixed types --")
mixed = [
    make_record(memory_id="t-ok-1", memory_type="operating_rule"),
    make_record(memory_id="t-ok-2", memory_type="ray_preference"),
    make_record(memory_id="t-bad-1", memory_type="fallback_rule"),
    make_record(memory_id="t-bad-2", memory_type="source_intake"),
    make_record(memory_id="t-bad-3", status="archived"),
]
with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
    for rec in mixed:
        f.write(json.dumps(rec) + "\n")
    tmp_path = Path(f.name)

sel, exc, all_r = load_and_filter(tmp_path, "batch1", 15, batch1_types)
tmp_path.unlink(missing_ok=True)
check("synthetic: 5 total records", len(all_r) == 5)
check("synthetic: 2 eligible (operating_rule + ray_preference)", len(sel) == 2)
check("synthetic: 3 excluded (fallback_rule, source_intake, archived)", len(exc) == 3)
check("synthetic: selected are valid types only", all(r["memory_type"] in batch1_types for r in sel))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
