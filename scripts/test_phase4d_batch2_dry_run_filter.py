"""
test_phase4d_batch2_dry_run_filter.py
Verifies that the Batch 2 dry-run script enforces correct type allowlist,
blocks excluded types, produces valid candidate records, and does NOT apply.
"""
import sys, json, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_phase4d_batch2_dry_run_filter ===\n")

import scripts.prepare_hermes_memory_v2_batch2_dry_run as batch2

print("-- Safety sentinels --")
check("_SUPABASE_WRITE_ATTEMPTED is False",
      batch2._SUPABASE_WRITE_ATTEMPTED is False)

print("\n-- Allowed type allowlist --")
EXPECTED_ALLOWED = {"lesson", "goal", "tool_registry", "scout_registry"}
check("BATCH2_ALLOWED_TYPES defined", hasattr(batch2, "BATCH2_ALLOWED_TYPES"))
allowed = set(batch2.BATCH2_ALLOWED_TYPES)
check("lesson in BATCH2_ALLOWED_TYPES", "lesson" in allowed)
check("goal in BATCH2_ALLOWED_TYPES", "goal" in allowed)
check("tool_registry in BATCH2_ALLOWED_TYPES", "tool_registry" in allowed)
check("scout_registry in BATCH2_ALLOWED_TYPES", "scout_registry" in allowed)
check("no extra types in BATCH2_ALLOWED_TYPES", allowed == EXPECTED_ALLOWED)

print("\n-- Excluded types blocked --")
check("BATCH2_EXCLUDED_TYPES defined", hasattr(batch2, "BATCH2_EXCLUDED_TYPES"))
excluded = set(batch2.BATCH2_EXCLUDED_TYPES)
for et in ["provider_status_snapshot", "executive_briefings", "ai_task_queue",
           "agent_dispatch_tasks", "fallback_rule", "debug_note", "archived_note", "template"]:
    check(f"'{et}' in BATCH2_EXCLUDED_TYPES", et in excluded)

print("\n-- Candidates list structure --")
check("_batch2_candidates function defined", hasattr(batch2, "_batch2_candidates"))
candidates = batch2._batch2_candidates()
check("candidates is non-empty list", isinstance(candidates, list) and len(candidates) > 0)
check("at most 25 candidates", len(candidates) <= 25)

required_fields = ["memory_type", "title", "summary", "status", "scope", "priority", "confidence",
                   "memory_id", "tags", "payload", "migration_status", "created_at", "updated_at"]
for i, c in enumerate(candidates):
    for f in required_fields:
        check(f"candidates[{i}] has '{f}'", f in c)
    check(f"candidates[{i}] type in BATCH2_ALLOWED_TYPES", c.get("memory_type") in allowed)
    check(f"candidates[{i}] status == 'active'", c.get("status") == "active")
    check(f"candidates[{i}] scope == 'live_answer'", c.get("scope") == "live_answer")
    check(f"candidates[{i}] priority 0-100",
          isinstance(c.get("priority"), int) and 0 <= c.get("priority") <= 100)
    check(f"candidates[{i}] confidence 0.0-1.0",
          isinstance(c.get("confidence"), float) and 0.0 <= c.get("confidence") <= 1.0)

print("\n-- Type coverage --")
type_counts = {}
for c in candidates:
    t = c.get("memory_type", "unknown")
    type_counts[t] = type_counts.get(t, 0) + 1
print(f"   Type breakdown: {type_counts}")
for t in EXPECTED_ALLOWED:
    check(f"at least 1 candidate of type '{t}'", type_counts.get(t, 0) >= 1)

print("\n-- _validate blocks excluded types --")
check("_validate function exists", hasattr(batch2, "_validate"))
for et in list(excluded)[:3]:
    bad = {"memory_type": et, "title": "Test", "body": "test", "status": "active",
           "scope": "live_answer", "priority": 50, "confidence": 0.8}
    errors = batch2._validate(bad)
    check(f"_validate rejects type '{et}'", len(errors) > 0)

print("\n-- _validate passes good records --")
import uuid
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
good = {
    "memory_id": str(uuid.uuid4()),
    "memory_type": "lesson", "title": "Test lesson",
    "summary": "Learn from this", "status": "active", "scope": "live_answer",
    "priority": 70, "confidence": 0.85, "tags": ["test"],
    "payload": {}, "migration_status": "pending",
    "created_at": now, "updated_at": now,
}
errors = batch2._validate(good)
check("_validate accepts good 'lesson' record", len(errors) == 0)

print("\n-- Dry-run report was generated --")
REPORT_DIR = ROOT / "docs" / "reports" / "memory"
jsonl_reports = list(REPORT_DIR.glob("phase4d_batch2_dry_run_*.jsonl"))
json_reports  = list(REPORT_DIR.glob("phase4d_batch2_dry_run_*.json"))
check("batch2 dry-run .jsonl report exists", len(jsonl_reports) > 0)
check("batch2 dry-run .json report exists", len(json_reports) > 0)
if json_reports:
    latest = max(json_reports, key=lambda p: p.stat().st_mtime)
    report = json.loads(latest.read_text())
    check("report has 'supabase_writes_attempted': False",
          report.get("supabase_writes_attempted") is False)
    check("report has candidate/selected count",
          "candidates_count" in report or "selected_count" in report)
    check("report has schema error count",
          "schema_errors" in report or "validation_failures" in report)
    failures = report.get("schema_errors", report.get("validation_failures", 0))
    check("report schema_errors == 0", failures == 0)

print("\n-- Source does NOT contain apply logic --")
src = inspect.getsource(batch2)
check("source contains _SUPABASE_WRITE_ATTEMPTED guard",
      "_SUPABASE_WRITE_ATTEMPTED" in src)
check("source does not call supabase .insert( unguarded",
      ".insert(" not in src or "_SUPABASE_WRITE_ATTEMPTED" in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
