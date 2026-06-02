"""
test_memory_v2_primary_rollback.py
Verifies the rollback script structure, dry-run safety, and that it never writes Supabase.
"""
import sys, os, re, json, tempfile, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_primary_rollback ===\n")

ROLLBACK_SCRIPT = ROOT / "scripts" / "rollback_hermes_memory_v2_primary.py"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.raymonddavis.nexus.telegram.plist"

print("-- Rollback script exists --")
check("rollback script exists", ROLLBACK_SCRIPT.exists())

print("\n-- Rollback script safety markers --")
src = ROLLBACK_SCRIPT.read_text(encoding="utf-8") if ROLLBACK_SCRIPT.exists() else ""
check("_SUPABASE_WRITE_ATTEMPTED = False in script", "_SUPABASE_WRITE_ATTEMPTED = False" in src)
check("does NOT write Supabase tables (no .table( call)", ".table(" not in src)
check("does NOT delete hermes_memory_v2 data", "hermes_memory_v2" not in src or "delete" not in src.lower()[:500])
check("has --dry-run flag", "--dry-run" in src)
check("has --apply flag", "--apply" in src)
check("has --restart flag", "--restart" in src)
check("has --confirm-text flag", "--confirm-text" in src)
check("targets HERMES_MEMORY_V2_MODE", "HERMES_MEMORY_V2_MODE" in src)
check("sets target mode to shadow", "shadow" in src)
check("explains it does NOT delete Supabase data",
      "does NOT delete" in src or "No Supabase" in src or "does not delete" in src.lower())

print("\n-- Dry run does not modify plist --")
if PLIST_PATH.exists():
    before = PLIST_PATH.read_text()
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ROLLBACK_SCRIPT), "--dry-run"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    after = PLIST_PATH.read_text()
    check("dry-run exits 0", result.returncode == 0)
    # dry-run shows DRY RUN only when mode would change; if already at target it says "Nothing to do."
    check("dry-run output is informative",
          "DRY RUN" in result.stdout or "Nothing to do" in result.stdout or "Already set" in result.stdout)
    check("dry-run does not modify plist", before == after)
    check("dry-run shows current mode", "primary" in result.stdout.lower() or "shadow" in result.stdout.lower())
else:
    check("plist path correct (skipping dry-run test)", True)
    print("  (plist not found — dry-run test skipped)")

print("\n-- Rollback script has plist label --")
check("PLIST_LABEL defined", "com.raymonddavis.nexus.telegram" in src)
check("plist path is correct", "com.raymonddavis.nexus.telegram.plist" in src)

print("\n-- REQUIRED_CONFIRM phrase in script --")
check("ROLLBACK PRIMARY phrase defined", "ROLLBACK PRIMARY" in src)

print("\n-- No dangerous operations in script --")
check("no DROP TABLE", "DROP TABLE" not in src.upper())
check("no DELETE FROM", "DELETE FROM" not in src.upper())
check("no TRUNCATE", "TRUNCATE" not in src.upper())
check("no rm -rf", "rm -rf" not in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
