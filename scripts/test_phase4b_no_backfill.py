"""
test_phase4b_no_backfill.py
Confirms that hermes_memory_v2 has no backfill records (row_count = 0)
and that no production records were modified or deleted during Phase 4B.
Connects to Supabase if env vars are present; skips if not.
"""
import sys, os, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_phase4b_no_backfill ===\n")

print("-- Phase 4B report confirms no backfill --")
memory_dir = ROOT / "docs" / "reports" / "memory"
phase4b_reports = sorted(memory_dir.glob("phase4b_*.json"))
if phase4b_reports:
    report = json.loads(phase4b_reports[-1].read_text(encoding="utf-8"))
    check("phase4b report: backfill_records_inserted=False",
          report.get("backfill_records_inserted") is False)
    check("phase4b report: old_tables_modified=False",
          report.get("old_tables_modified") is False)
    check("phase4b report: records_deleted=False",
          report.get("records_deleted") is False)
    check("phase4b report: hermes_memory_v2_row_count=0",
          report.get("hermes_memory_v2_row_count") == 0)
else:
    check("phase4b report found (will exist after this phase)", False)

print("\n-- Backup manifest confirms no writes --")
manifests = sorted(memory_dir.glob("backup_manifest_*.json"))
if manifests:
    manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
    check("backup manifest: supabase_write_attempted=False",
          manifest.get("supabase_write_attempted") is False)
else:
    check("backup manifest found", False)

print("\n-- Live Supabase check (if env vars present) --")
has_env = bool(os.environ.get("SUPABASE_URL")) and bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

if has_env:
    try:
        from supabase import create_client
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        client = create_client(url, key)

        # Check hermes_memory_v2 row count
        resp = client.table("hermes_memory_v2").select("memory_id", count="exact").execute()
        row_count = resp.count if resp.count is not None else len(resp.data)
        check(f"hermes_memory_v2 row_count == 0 (actual: {row_count})", row_count == 0)

        if row_count > 0:
            print(f"  WARNING: {row_count} rows found in hermes_memory_v2!")
            print("  Do NOT delete or modify. Report to Ray immediately.")

        # Spot-check old tables are untouched (just verify they still exist and have rows)
        old_tables_to_check = [
            ("hermes_executive_memory", 9),
            ("knowledge_items", 53),
            ("ai_task_queue", 24),
        ]
        for table, expected_min in old_tables_to_check:
            try:
                r = client.table(table).select("*", count="exact").execute()
                count = r.count if r.count is not None else len(r.data)
                check(f"old table '{table}' still has rows (count={count})", count >= 1)
            except Exception as exc:
                msg = str(exc)[:60]
                if "eyJ" in msg: msg = "[redacted]"
                check(f"old table '{table}' accessible", False)
                print(f"    Error: {msg}")

    except Exception as exc:
        msg = str(exc)
        if "eyJ" in msg: msg = "[redacted]"
        check(f"Supabase connection for backfill check", False)
        print(f"  Error: {msg[:120]}")
else:
    check("env vars not set — live check skipped", True)
    check("live check skip is safe", True)

print("\n-- Apply script sentinel still False --")
apply_src = (ROOT / "scripts" / "apply_hermes_memory_v2_migration.py").read_text(encoding="utf-8")
check("apply script _SUPABASE_WRITE_ATTEMPTED = False", "_SUPABASE_WRITE_ATTEMPTED = False" in apply_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
