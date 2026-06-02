"""
test_apply_migration_refuses_stale_backup.py
Verifies that apply_hermes_memory_v2_migration.py refuses to apply
when the backup manifest is stale (>24h old) or ready_for_phase4b=False.
Uses synthetic fixtures — no real Supabase data.
"""
import sys, subprocess, json, shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
APPLY_SCRIPT = ROOT / "scripts" / "apply_hermes_memory_v2_migration.py"
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"
FIXTURES = ROOT / "tests" / "fixtures" / "memory_backup"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def run_apply(timeout=15) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(APPLY_SCRIPT),
         "--apply", "--require-ray-approval",
         "--confirm-text", "I APPROVE HERMES MEMORY V2 MIGRATION"],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode, result.stdout + result.stderr


def install_fixture(fixture_path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = MEMORY_DIR / f"backup_manifest_{ts}_test.json"
    shutil.copy(fixture_path, dest)
    return dest


def remove_fixture(p: Path):
    if p.exists():
        p.unlink()


print("=== test_apply_migration_refuses_stale_backup ===\n")

check("apply script exists", APPLY_SCRIPT.exists())
check("stale fixture exists", (FIXTURES / "fake_stale_manifest.json").exists())
check("valid fixture exists", (FIXTURES / "fake_backup_manifest.json").exists())

if not APPLY_SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = APPLY_SCRIPT.read_text(encoding="utf-8")

print("\n-- Staleness constant defined --")
check("BACKUP_MANIFEST_MAX_AGE_H defined", "BACKUP_MANIFEST_MAX_AGE_H" in src)
check("Max age is 24h", "24" in src)

print("\n-- Age comparison uses timedelta --")
check("timedelta imported or used", "timedelta" in src)
check("age comparison present", "age >" in src or "age>" in src)

print("\n-- Apply blocked on stale manifest (runtime) --")
existing = sorted(MEMORY_DIR.glob("backup_manifest_*.json"))
renamed = []
for p in existing:
    tmp = p.with_suffix(".json.bak")
    p.rename(tmp)
    renamed.append((tmp, p))

stale_installed = install_fixture(FIXTURES / "fake_stale_manifest.json")
try:
    code, out = run_apply()
    check("apply blocked when manifest is stale (exit non-zero)", code != 0)
    check("output mentions stale or age or 24", "stale" in out.lower() or "age" in out.lower() or "24" in out or "old" in out.lower())
    check("output mentions manifest", "manifest" in out.lower())
finally:
    remove_fixture(stale_installed)
    for tmp, orig in renamed:
        tmp.rename(orig)

print("\n-- Apply blocked when ready_for_phase4b=False --")
not_ready_manifest = {
    "manifest_version": "1.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "mode": "export",
    "exported": False,
    "ready_for_phase4b": False,
    "output_dir": "backups/test",
    "tables": [],
    "local_file_snapshots": [],
    "gitignore_check": True,
    "supabase_write_attempted": False,
}
existing2 = sorted(MEMORY_DIR.glob("backup_manifest_*.json"))
renamed2 = []
for p in existing2:
    tmp = p.with_suffix(".json.bak")
    p.rename(tmp)
    renamed2.append((tmp, p))

ts2 = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
not_ready_path = MEMORY_DIR / f"backup_manifest_{ts2}_notready.json"
not_ready_path.write_text(json.dumps(not_ready_manifest, indent=2), encoding="utf-8")

try:
    code2, out2 = run_apply()
    check("apply blocked when ready_for_phase4b=False (exit non-zero)", code2 != 0)
    check("output mentions ready_for_phase4b or not ready", "ready" in out2.lower() or "phase4b" in out2.lower())
finally:
    remove_fixture(not_ready_path)
    for tmp, orig in renamed2:
        tmp.rename(orig)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
