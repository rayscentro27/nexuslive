"""
test_supabase_backup_manifest.py
Verifies the backup manifest JSON format and required fields,
using synthetic test fixtures (no real user data).
"""
import sys, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "memory_backup"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_supabase_backup_manifest ===\n")

print("-- Fixture directory exists --")
check("tests/fixtures/memory_backup/ exists", FIXTURES.exists())

print("\n-- Fake backup manifest fixture --")
fake_manifest_path = FIXTURES / "fake_backup_manifest.json"
check("fake_backup_manifest.json exists", fake_manifest_path.exists())

if not fake_manifest_path.exists():
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(FAIL)

manifest = json.loads(fake_manifest_path.read_text(encoding="utf-8"))

print("\n-- Required top-level fields --")
required_fields = [
    "manifest_version", "generated_at", "mode", "exported",
    "ready_for_phase4b", "output_dir", "tables",
    "local_file_snapshots", "gitignore_check", "supabase_write_attempted",
]
for f in required_fields:
    check(f"field '{f}' present", f in manifest)

print("\n-- Safety field values --")
check("supabase_write_attempted is False", manifest.get("supabase_write_attempted") is False)
check("ready_for_phase4b is True in valid manifest", manifest.get("ready_for_phase4b") is True)
check("gitignore_check is True in valid manifest", manifest.get("gitignore_check") is True)

print("\n-- Tables list format --")
tables = manifest.get("tables", [])
check("tables list has 12 entries", len(tables) == 12)
EXPECTED_TABLES = [
    "ai_memory", "hermes_executive_memory", "hermes_response_patterns",
    "memory_links", "knowledge_items", "business_opportunities",
    "executive_briefings", "provider_health", "ai_task_queue",
    "agent_dispatch_tasks", "human_approval_requests", "nexus_skills",
]
for t in EXPECTED_TABLES:
    found = any(entry.get("table") == t for entry in tables)
    check(f"table '{t}' in tables list", found)
for entry in tables:
    check(f"entry '{entry.get('table')}' has 'file' field", "file" in entry)
    check(f"entry '{entry.get('table')}' has 'exported' field", "exported" in entry)

print("\n-- generated_at is parseable ISO timestamp --")
generated_at_str = manifest.get("generated_at", "")
try:
    dt = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
    check("generated_at parses as UTC datetime", dt.tzinfo is not None)
except Exception:
    check("generated_at parses as UTC datetime", False)

print("\n-- local_file_snapshots format --")
snapshots = manifest.get("local_file_snapshots", [])
check("local_file_snapshots has 7 entries", len(snapshots) == 7)
for snap in snapshots:
    check(f"snapshot '{snap.get('path')}' has 'exists' field", "exists" in snap)

print("\n-- Stale manifest fixture --")
stale_path = FIXTURES / "fake_stale_manifest.json"
check("fake_stale_manifest.json exists", stale_path.exists())
if stale_path.exists():
    stale = json.loads(stale_path.read_text(encoding="utf-8"))
    check("stale manifest has ready_for_phase4b=False", stale.get("ready_for_phase4b") is False)
    check("stale manifest has old generated_at", "2026-05" in stale.get("generated_at", ""))

print("\n-- Fake table export fixture --")
export_path = FIXTURES / "fake_table_export.json"
check("fake_table_export.json exists", export_path.exists())
if export_path.exists():
    export_data = json.loads(export_path.read_text(encoding="utf-8"))
    check("fake export has 'table' field", "table" in export_data)
    check("fake export has 'rows' field", "rows" in export_data)
    check("fake export has 'note' field marking it synthetic", "note" in export_data)
    check("fake export note says SYNTHETIC", "SYNTHETIC" in export_data.get("note", ""))
    check("fake export has no real user data", export_data.get("row_count", 0) <= 10)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
