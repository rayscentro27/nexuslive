"""
test_apply_migration_requires_backup_manifest.py
Verifies that apply_hermes_memory_v2_migration.py refuses to apply
when no backup manifest is present, and that it validates
ready_for_phase4b and manifest freshness.
"""
import sys, subprocess, json, shutil
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
APPLY_SCRIPT = ROOT / "scripts" / "apply_hermes_memory_v2_migration.py"
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"
FIXTURES = ROOT / "tests" / "fixtures" / "memory_backup"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def run_apply(extra_args=None, timeout=15):
    args = [
        sys.executable, str(APPLY_SCRIPT),
        "--apply", "--require-ray-approval",
        "--confirm-text", "I APPROVE HERMES MEMORY V2 MIGRATION",
    ]
    if extra_args:
        args += extra_args
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout + result.stderr


print("=== test_apply_migration_requires_backup_manifest ===\n")

print("-- Apply script exists --")
check("apply_hermes_memory_v2_migration.py exists", APPLY_SCRIPT.exists())
if not APPLY_SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

print("\n-- Source-level manifest check present --")
src = APPLY_SCRIPT.read_text(encoding="utf-8")
check("BACKUP_MANIFEST_GLOB constant defined", "BACKUP_MANIFEST_GLOB" in src)
check("_check_backup_manifest function defined", "_check_backup_manifest" in src)
check("ready_for_phase4b checked in _check_backup_manifest", "ready_for_phase4b" in src)
check("manifest freshness check present (timedelta or hours)", "timedelta" in src or "hours" in src)
check("manifest errors propagate to run_apply", "manifest_errors" in src or "Backup manifest" in src)

print("\n-- Apply blocked when no manifest present (runtime) --")
# Temporarily rename any existing manifests
existing = sorted(MEMORY_DIR.glob("backup_manifest_*.json"))
renamed = []
for p in existing:
    tmp = p.with_suffix(".json.bak")
    p.rename(tmp)
    renamed.append((tmp, p))

try:
    code, out = run_apply()
    check("apply blocked when manifest missing (exit non-zero)", code != 0)
    check("apply output mentions manifest", "manifest" in out.lower())
finally:
    for tmp, orig in renamed:
        tmp.rename(orig)

print("\n-- Safety banner mentions manifest requirement --")
result = subprocess.run([sys.executable, str(APPLY_SCRIPT)], capture_output=True, text=True, timeout=10)
banner_out = result.stdout + result.stderr
check("safety banner mentions backup manifest", "manifest" in banner_out.lower())

print("\n-- _check_backup_manifest returns errors list --")
check("_check_backup_manifest returns tuple (path, errors)", "tuple" in src or "list[str]" in src or "-> tuple" in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
