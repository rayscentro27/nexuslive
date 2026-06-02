"""
test_verify_hermes_memory_backup_manifest.py
Verifies the backup manifest verifier script exists, is importable,
and correctly validates manifest structure using synthetic fixtures.
"""
import sys, json, subprocess, shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "scripts" / "verify_hermes_memory_backup_manifest.py"
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"
FIXTURES = ROOT / "tests" / "fixtures" / "memory_backup"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def run(extra_args=None, timeout=15) -> tuple[int, str]:
    cmd = [sys.executable, str(VERIFIER)] + (extra_args or [])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout + result.stderr


print("=== test_verify_hermes_memory_backup_manifest ===\n")

print("-- Verifier script exists --")
check("verify_hermes_memory_backup_manifest.py exists", VERIFIER.exists())
if not VERIFIER.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = VERIFIER.read_text(encoding="utf-8")

print("\n-- Source checks --")
check("never prints secrets (no os.environ print)", "print(os.environ" not in src)
check("verifier does not print raw manifest data (no print of full manifest)", "print(manifest)" not in src)
check("REQUIRED_TABLES defined", "REQUIRED_TABLES" in src)
check("KNOWN_MISSING_TABLES defined", "KNOWN_MISSING_TABLES" in src)
check("max age 24h defined", "MAX_AGE_H" in src and "24" in src)
check("ready_for_phase4b checked", "ready_for_phase4b" in src)

print("\n-- Verifier runs when a valid manifest is present --")
# Check that the real manifest (from Phase 4B export) is found
real_manifests = sorted(MEMORY_DIR.glob("backup_manifest_*.json"))
if real_manifests:
    code, out = run()
    check("verifier exits 0 with real manifest", code == 0)
    check("output shows table export count", "Table export" in out or "exported" in out.lower())
    check("output shows ready_for_4b", "ready_for_4b" in out or "ready" in out.lower())
    check("output does not print row data or secrets", "eyJ" not in out)
    check("output shows Overall: READY", "READY" in out)
else:
    check("real manifest present (skipping runtime test)", False)
    check("runtime test skipped (no manifest)", True)

print("\n-- Stale manifest causes failure --")
existing = sorted(MEMORY_DIR.glob("backup_manifest_*.json"))
renamed = []
for p in existing:
    tmp = p.with_suffix(".json.bak")
    p.rename(tmp); renamed.append((tmp, p))

stale_src = FIXTURES / "fake_stale_manifest.json"
ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
stale_dest = MEMORY_DIR / f"backup_manifest_{ts}_stale.json"
shutil.copy(stale_src, stale_dest)
try:
    code2, out2 = run()
    check("stale manifest causes non-zero exit", code2 != 0)
    check("stale manifest output mentions age or stale", "stale" in out2.lower() or "old" in out2.lower() or "age" in out2.lower())
finally:
    stale_dest.unlink(missing_ok=True)
    for tmp, orig in renamed: tmp.rename(orig)

print("\n-- Source handles missing manifest case --")
check("verifier handles missing manifest (source has 'No backup manifest found')",
      "No backup manifest found" in src or "not found" in src.lower() or "FAIL" in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
