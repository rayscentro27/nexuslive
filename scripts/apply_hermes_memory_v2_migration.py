"""
apply_hermes_memory_v2_migration.py
Phase 4A — Guarded migration apply script for hermes_memory_v2.

DEFAULT BEHAVIOR: No-op. Prints warnings and exits safely.
Nothing is applied unless --apply + --require-ray-approval + exact confirmation text
are ALL present simultaneously.

Usage:
  python scripts/apply_hermes_memory_v2_migration.py --dry-run
  python scripts/apply_hermes_memory_v2_migration.py --apply \\
      --require-ray-approval \\
      --confirm-text "I APPROVE HERMES MEMORY V2 MIGRATION"
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE_DEFAULT = ROOT / "supabase" / "migrations" / "20260602004443_create_hermes_memory_v2.sql"
BACKUP_PLAN_GLOB = "hermes_memory_v2_backup_plan_*.md"
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

REQUIRED_CONFIRM_TEXT = "I APPROVE HERMES MEMORY V2 MIGRATION"

# Secrets that must NEVER be printed
_SECRET_KEYS = [
    "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY", "SUPABASE_ANON_KEY",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
    "HERMES_GATEWAY_KEY", "OANDA_API_KEY", "ACCESS_TOKEN",
    "PRIVATE_KEY", "PASSWORD", "SECRET",
]

_SUPABASE_WRITE_ATTEMPTED = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_env(key: str) -> bool:
    """Return True if env var is set; never print its value."""
    return bool(os.environ.get(key, "").strip())


def _check_secrets_present() -> list[str]:
    """Return list of missing required env vars (without printing their values)."""
    required = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing = [k for k in required if not _safe_env(k)]
    return missing


def _check_backup_exists() -> Path | None:
    """Return path to most recent backup plan, or None if missing."""
    candidates = sorted(MEMORY_DIR.glob(BACKUP_PLAN_GLOB))
    return candidates[-1] if candidates else None


def _check_migration_file(migration_file: Path) -> bool:
    return migration_file.exists() and migration_file.stat().st_size > 0


def print_safety_banner() -> None:
    print("=" * 70)
    print("  HERMES MEMORY V2 MIGRATION GUARD")
    print("  Phase 4A — Schema + Guardrails Only")
    print("=" * 70)
    print()
    print("  SAFETY CONSTRAINTS:")
    print("  - This script does NOT apply anything by default.")
    print("  - --apply requires --require-ray-approval.")
    print("  - --apply requires exact confirmation text.")
    print("  - --apply requires backup plan to exist.")
    print("  - --apply requires environment secrets to be set.")
    print("  - --dry-run never connects to Supabase.")
    print("  - No secrets are printed by this script.")
    print()


def run_dry_run(migration_file: Path) -> int:
    print("[DRY RUN] No Supabase connection. No changes applied.")
    print()

    print(f"  Migration file : {migration_file.relative_to(ROOT)}")
    exists = _check_migration_file(migration_file)
    print(f"  File exists    : {'YES' if exists else 'NO — MISSING'}")
    if not exists:
        print("  ERROR: Migration file not found. Cannot proceed.")
        return 1

    backup = _check_backup_exists()
    print(f"  Backup plan    : {backup.name if backup else 'MISSING'}")

    missing_secrets = _check_secrets_present()
    if missing_secrets:
        print(f"  Env secrets    : MISSING ({', '.join(missing_secrets)})")
    else:
        print("  Env secrets    : SET (values not printed)")

    print()
    print("[DRY RUN] Command that WOULD be run if Ray approves:")
    print()
    print("    supabase db push --db-url $SUPABASE_DB_URL")
    print("    # OR: supabase migration up --linked")
    print()
    print("[DRY RUN] Supabase data changed: NO")
    print("[DRY RUN] Migration applied: NO")
    return 0


def run_default_info(migration_file: Path) -> int:
    print("  Mode: DEFAULT (no flags — safe no-op)")
    print()
    print(f"  Migration file : {migration_file.relative_to(ROOT)}")
    print(f"  File exists    : {'YES' if _check_migration_file(migration_file) else 'NO'}")
    backup = _check_backup_exists()
    print(f"  Backup plan    : {backup.name if backup else 'NOT FOUND'}")
    print()
    print("  To run dry-run only:")
    print("    python scripts/apply_hermes_memory_v2_migration.py --dry-run")
    print()
    print("  To apply (requires Ray approval + confirmation text):")
    print('    python scripts/apply_hermes_memory_v2_migration.py \\')
    print('        --apply \\')
    print('        --require-ray-approval \\')
    print(f'        --confirm-text "{REQUIRED_CONFIRM_TEXT}"')
    print()
    print("  Supabase data changed: NO")
    print("  Migration applied: NO")
    return 0


def run_apply(args: argparse.Namespace, migration_file: Path) -> int:
    print("[APPLY MODE] Running pre-apply safety checks...")
    print()

    errors: list[str] = []

    # Guard 1: --require-ray-approval must be present
    if not args.require_ray_approval:
        errors.append("--require-ray-approval flag is missing. Ray must explicitly authorize apply.")

    # Guard 2: exact confirmation text
    provided = (args.confirm_text or "").strip()
    if provided != REQUIRED_CONFIRM_TEXT:
        errors.append(
            f"Confirmation text mismatch.\n"
            f"  Required: {REQUIRED_CONFIRM_TEXT!r}\n"
            f"  Provided: {provided!r}"
        )

    # Guard 3: migration file exists
    if not _check_migration_file(migration_file):
        errors.append(f"Migration file not found: {migration_file}")

    # Guard 4: backup plan must exist
    backup = _check_backup_exists()
    if not backup:
        errors.append(
            "Backup plan not found. Run backup export before applying migration. "
            f"Expected: {MEMORY_DIR}/{BACKUP_PLAN_GLOB}"
        )

    # Guard 5: env secrets must be set
    missing_secrets = _check_secrets_present()
    if missing_secrets:
        errors.append(
            f"Required environment variables not set: {', '.join(missing_secrets)}. "
            "Set them before applying. Values are never printed by this script."
        )

    if errors:
        print("  APPLY BLOCKED — pre-apply checks failed:")
        print()
        for i, err in enumerate(errors, 1):
            print(f"  [{i}] {err}")
        print()
        print("  Supabase data changed: NO")
        print("  Migration applied: NO")
        return 1

    # All guards passed — print the command that WOULD be run, but do not execute
    print("  All pre-apply checks passed.")
    print()
    print("  PHASE 4A RESTRICTION: Migration apply is not executed in Phase 4A.")
    print("  Phase 4A only creates the schema plan. Apply occurs in Phase 4B.")
    print()
    print("  Command that would be run in Phase 4B:")
    print()
    print("    supabase db push --db-url $SUPABASE_DB_URL")
    print()
    print("  Supabase data changed: NO")
    print("  Migration applied: NO (Phase 4A restriction)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guarded migration apply script for hermes_memory_v2 (Phase 4A)."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate migration file and print intended command. No Supabase connection.")
    parser.add_argument("--apply", action="store_true",
                        help="Attempt to apply migration. Requires --require-ray-approval and exact confirm text.")
    parser.add_argument("--require-ray-approval", action="store_true",
                        help="Confirms Ray has approved this migration.")
    parser.add_argument("--confirm-text", type=str, default="",
                        help=f'Must equal exactly: "{REQUIRED_CONFIRM_TEXT}"')
    parser.add_argument("--migration-file", type=str, default="",
                        help="Path to SQL migration file (default: Phase 4A migration).")
    args = parser.parse_args()

    migration_file = Path(args.migration_file) if args.migration_file else MIGRATION_FILE_DEFAULT

    print_safety_banner()
    print(f"  Timestamp: {_now()}")
    print(f"  Migration: {migration_file.relative_to(ROOT) if migration_file.is_relative_to(ROOT) else migration_file}")
    print()

    if args.apply:
        return run_apply(args, migration_file)
    elif args.dry_run:
        return run_dry_run(migration_file)
    else:
        return run_default_info(migration_file)


if __name__ == "__main__":
    sys.exit(main())
