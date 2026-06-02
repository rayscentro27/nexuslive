"""
verify_hermes_memory_backup_manifest.py
Verifies the latest backup manifest is complete, recent, and ready for Phase 4B.
Prints only non-sensitive summary information. Never prints secrets or row data.
"""
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"
BACKUPS_DIR = ROOT / "backups"
MAX_AGE_H = 24

REQUIRED_TABLES = [
    "hermes_executive_memory", "hermes_response_patterns", "knowledge_items",
    "business_opportunities", "executive_briefings", "provider_health",
    "ai_task_queue", "agent_dispatch_tasks", "human_approval_requests", "nexus_skills",
]
# These tables were in the backup plan but do not exist in this Supabase project
KNOWN_MISSING_TABLES = {"ai_memory", "memory_links"}


def find_latest_manifest() -> tuple[Path | None, dict | None]:
    # Check docs/reports/memory/ first (report copies), then backups/
    for pattern_dir, glob in [
        (MEMORY_DIR, "backup_manifest_*.json"),
        (BACKUPS_DIR, "**/backup_manifest.json"),
    ]:
        candidates = sorted(pattern_dir.glob(glob))
        if candidates:
            p = candidates[-1]
            try:
                return p, json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None, None


def main() -> int:
    print("=== Backup Manifest Verification ===\n")

    manifest_path, manifest = find_latest_manifest()

    if not manifest_path or not manifest:
        print("FAIL: No backup manifest found.")
        print(f"  Searched: {MEMORY_DIR} and {BACKUPS_DIR}")
        print("  Run export script with --write-manifest first.")
        return 1

    print(f"Manifest path : {manifest_path.relative_to(ROOT) if manifest_path.is_relative_to(ROOT) else manifest_path}")

    generated_at_str = manifest.get("generated_at", "")
    print(f"Created at    : {generated_at_str}")

    # Age check
    age_ok = False
    age_str = "unknown"
    if generated_at_str:
        try:
            generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - generated_at
            age_h = age.total_seconds() / 3600
            age_str = f"{age_h:.1f}h"
            age_ok = age <= timedelta(hours=MAX_AGE_H)
        except ValueError:
            age_str = "parse error"

    print(f"Age           : {age_str} (max {MAX_AGE_H}h) — {'PASS' if age_ok else 'FAIL — too old'}")

    ready = manifest.get("ready_for_phase4b", False)
    print(f"ready_for_4b  : {ready} — {'PASS' if ready else 'FAIL'}")

    write_attempted = manifest.get("supabase_write_attempted", True)
    print(f"writes_safe   : supabase_write_attempted={write_attempted} — {'PASS' if not write_attempted else 'FAIL'}")

    gitignore_ok = manifest.get("gitignore_check", False)
    print(f"gitignore     : {gitignore_ok} — {'PASS' if gitignore_ok else 'FAIL'}")

    # Table summary — counts only, no row data
    tables = manifest.get("tables", [])
    exported = [t for t in tables if t.get("exported")]
    skipped = [t for t in tables if not t.get("exported")]
    known_missing = [t for t in skipped if t.get("table") in KNOWN_MISSING_TABLES]
    unexpected_missing = [t for t in skipped if t.get("table") not in KNOWN_MISSING_TABLES]

    print(f"\nTable export  : {len(exported)}/{len(tables)} exported")
    for t in exported:
        count = t.get("row_count", "?")
        print(f"  ✓ {t['table']}: {count} rows")
    if known_missing:
        print(f"Known absent  : {len(known_missing)} (not in this Supabase project)")
        for t in known_missing:
            print(f"  - {t['table']} (expected absent)")
    if unexpected_missing:
        print(f"Unexpected skip: {len(unexpected_missing)}")
        for t in unexpected_missing:
            print(f"  ! {t['table']}: {t.get('error', 'unknown error')[:120]}")

    # Required tables check
    exported_names = {t["table"] for t in exported}
    missing_required = [t for t in REQUIRED_TABLES if t not in exported_names]
    tables_ok = len(missing_required) == 0
    print(f"\nRequired tables: {'PASS' if tables_ok else 'FAIL — missing: ' + str(missing_required)}")

    # Local files summary
    snapshots = manifest.get("local_file_snapshots", [])
    snapped = [s for s in snapshots if s.get("exists")]
    print(f"Local files   : {len(snapped)}/{len(snapshots)} copied")

    # Overall verdict
    all_ok = age_ok and ready and not write_attempted and gitignore_ok and tables_ok
    print(f"\nOverall       : {'READY — proceed to migration apply' if all_ok else 'NOT READY — fix issues above'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
