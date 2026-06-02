"""
export_supabase_memory_backup.py
Default: dry-run only. Prints what would be exported. No DB connection.
--export requires --confirm-text 'I APPROVE HERMES MEMORY BACKUP EXPORT'.
Never prints Supabase keys. Never auto-commits backups.
"""
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Safety sentinel — never set to True in this file
_SUPABASE_WRITE_ATTEMPTED = False

REQUIRED_CONFIRM_TEXT = "I APPROVE HERMES MEMORY BACKUP EXPORT"

MEMORY_TABLES = [
    "ai_memory",
    "hermes_executive_memory",
    "hermes_response_patterns",
    "memory_links",
    "knowledge_items",
    "business_opportunities",
    "executive_briefings",
    "provider_health",
    "ai_task_queue",
    "agent_dispatch_tasks",
    "human_approval_requests",
    "nexus_skills",
]

LOCAL_FILES = [
    "lib/hermes_memory_freshness.py",
    "lib/hermes_conversation_context_resolver.py",
    "scripts/generate_hermes_memory_v2_dry_run.py",
    "docs/HERMES_MEMORY_V2_SCHEMA.md",
    "supabase/migrations/20260602004443_create_hermes_memory_v2.sql",
    "scripts/apply_hermes_memory_v2_migration.py",
    "scripts/export_supabase_memory_backup.py",
]

GITIGNORE_MUST_INCLUDE = "backups/"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _check_gitignore() -> tuple[bool, str]:
    gi = ROOT / ".gitignore"
    if not gi.exists():
        return False, ".gitignore not found"
    content = gi.read_text(encoding="utf-8")
    if GITIGNORE_MUST_INCLUDE in content:
        return True, f"'{GITIGNORE_MUST_INCLUDE}' present in .gitignore"
    return False, f"'{GITIGNORE_MUST_INCLUDE}' NOT found in .gitignore — backups would be committed!"


def _safe_env_check() -> dict:
    url_set = bool(os.environ.get("SUPABASE_URL", "").strip())
    key_set = bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip())
    missing = []
    if not url_set:
        missing.append("SUPABASE_URL")
    if not key_set:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "url_set": url_set,
        "key_set": key_set,
        "missing": missing,
        "ready": url_set and key_set,
    }


def _build_manifest(output_dir: Path, tables: list[str], include_local: bool,
                    mode: str, exported: bool) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    local_snapshots = []
    if include_local:
        for rel in LOCAL_FILES:
            p = ROOT / rel
            local_snapshots.append({
                "path": rel,
                "exists": p.exists(),
                "size_bytes": p.stat().st_size if p.exists() else None,
            })
    return {
        "manifest_version": "1.0",
        "generated_at": ts,
        "mode": mode,
        "exported": exported,
        "ready_for_phase4b": exported,
        "output_dir": str(output_dir),
        "tables": [{"table": t, "file": f"{t}.json", "exported": exported} for t in tables],
        "local_file_snapshots": local_snapshots,
        "gitignore_check": _check_gitignore()[0],
        "supabase_write_attempted": False,
    }


def cmd_dry_run(args) -> int:
    print("=== Backup Export Dry-Run ===\n")
    gi_ok, gi_msg = _check_gitignore()
    print(f"Gitignore check: {'PASS' if gi_ok else 'FAIL'} — {gi_msg}")
    if not gi_ok:
        print("ERROR: Fix .gitignore before exporting. Aborting.")
        return 1

    env = _safe_env_check()
    if env["missing"]:
        print(f"Env secrets: MISSING ({', '.join(env['missing'])}) — expected in dry-run, would be required for --export")
    else:
        print("Env secrets: SET (not printed)")

    tables = MEMORY_TABLES if args.tables == "memory" else []
    ts = _ts()
    output_dir = ROOT / "backups" / f"supabase_memory_migration_{ts}"

    print(f"\nWould export {len(tables)} tables to: {output_dir}")
    for t in tables:
        print(f"  → {t}.json")

    if args.include_local_files:
        print(f"\nWould snapshot {len(LOCAL_FILES)} local files:")
        for f in LOCAL_FILES:
            print(f"  → {f}")

    manifest = _build_manifest(output_dir, tables, args.include_local_files, "dry_run", False)
    print(f"\nManifest would be written to: {output_dir}/backup_manifest.json")
    print(f"  ready_for_phase4b: {manifest['ready_for_phase4b']}")
    print(f"  supabase_write_attempted: {manifest['supabase_write_attempted']}")
    print("\nDry-run complete. No files written. No DB connection made.")
    return 0


def cmd_export(args) -> int:
    if not args.confirm_text or args.confirm_text.strip() != REQUIRED_CONFIRM_TEXT:
        print("ERROR: --export requires --confirm-text exactly:")
        print(f'  "{REQUIRED_CONFIRM_TEXT}"')
        print("Received:", repr(getattr(args, "confirm_text", None)))
        return 1

    gi_ok, gi_msg = _check_gitignore()
    if not gi_ok:
        print(f"ERROR: Gitignore check failed — {gi_msg}")
        print("Fix .gitignore before exporting. Aborting.")
        return 1

    env = _safe_env_check()
    if not env["ready"]:
        print(f"ERROR: Required env secrets not set: {', '.join(env['missing'])}")
        print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running --export.")
        return 1

    tables = MEMORY_TABLES if args.tables == "memory" else []
    ts = _ts()
    output_dir = (Path(args.output_dir) if args.output_dir
                  else ROOT / "backups" / f"supabase_memory_migration_{ts}")

    print(f"=== Backup Export ===\n")
    print(f"Output directory: {output_dir}")
    print(f"Tables to export: {len(tables)}")
    print()
    print("NOTE: Phase 4A.5 — export not yet wired to live Supabase client.")
    print("      This script validates guardrails only.")
    print("      Actual row export requires Phase 4B Ray approval.")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = _build_manifest(output_dir, tables, args.include_local_files, "export", False)
    manifest_path = output_dir / "backup_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest written: {manifest_path}")

    if args.write_manifest:
        report_dir = ROOT / "docs" / "reports" / "memory"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"backup_manifest_{ts}.json"
        report_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Report copy written: {report_path}")

    print(f"\nsupabase_write_attempted: {manifest['supabase_write_attempted']}")
    print("Export guardrails verified. No live Supabase rows exported yet (Phase 4B required).")
    return 0


def cmd_verify_only(args) -> int:
    print("=== Verify-Only Mode ===\n")
    gi_ok, gi_msg = _check_gitignore()
    print(f"Gitignore:  {'PASS' if gi_ok else 'FAIL'} — {gi_msg}")

    env = _safe_env_check()
    env_status = "READY" if env["ready"] else f"MISSING ({', '.join(env['missing'])})"
    print(f"Env secrets: {env_status}")

    migration_file = ROOT / "supabase" / "migrations" / "20260602004443_create_hermes_memory_v2.sql"
    print(f"Migration file: {'EXISTS' if migration_file.exists() else 'MISSING'}")

    backup_plan_files = sorted((ROOT / "docs" / "reports" / "memory").glob("hermes_memory_v2_backup_plan_*.md"))
    print(f"Backup plan docs: {len(backup_plan_files)} found")

    manifest_files = sorted((ROOT / "docs" / "reports" / "memory").glob("backup_manifest_*.json"))
    print(f"Backup manifests: {len(manifest_files)} found")
    if manifest_files:
        latest = json.loads(manifest_files[-1].read_text(encoding="utf-8"))
        print(f"  Latest: {manifest_files[-1].name}")
        print(f"  ready_for_phase4b: {latest.get('ready_for_phase4b', 'N/A')}")

    all_ok = gi_ok and migration_file.exists() and len(backup_plan_files) >= 1
    print(f"\nOverall: {'READY for --export review' if all_ok else 'NOT READY'}")
    return 0 if all_ok else 1


def main():
    parser = argparse.ArgumentParser(description="Export Hermes/Nexus memory backup (default: dry-run)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True,
                       help="Print what would be exported (default)")
    group.add_argument("--export", action="store_true",
                       help="Run actual export (requires --confirm-text)")
    group.add_argument("--verify-only", action="store_true",
                       help="Check gitignore, env, and manifest without exporting")

    parser.add_argument("--confirm-text", type=str, default="",
                        help=f'Must equal exactly: "{REQUIRED_CONFIRM_TEXT}"')
    parser.add_argument("--output-dir", type=str, default="",
                        help="Override output directory (default: backups/supabase_memory_migration_<ts>)")
    parser.add_argument("--tables", type=str, default="memory",
                        help="Table group to export: 'memory' (default)")
    parser.add_argument("--include-local-files", action="store_true",
                        help="Include local file snapshots in manifest")
    parser.add_argument("--write-manifest", action="store_true",
                        help="Write manifest copy to docs/reports/memory/")

    args = parser.parse_args()

    if args.verify_only:
        sys.exit(cmd_verify_only(args))
    elif args.export:
        sys.exit(cmd_export(args))
    else:
        sys.exit(cmd_dry_run(args))


if __name__ == "__main__":
    main()
