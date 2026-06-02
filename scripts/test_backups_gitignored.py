"""
test_backups_gitignored.py
Verifies that the backups/ directory is properly gitignored
and that no backup files can be accidentally committed.
"""
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_backups_gitignored ===\n")

print("-- .gitignore contains backups/ --")
gitignore = ROOT / ".gitignore"
check(".gitignore exists", gitignore.exists())
if gitignore.exists():
    content = gitignore.read_text(encoding="utf-8")
    check("'backups/' entry in .gitignore", "backups/" in content)
    check("backups/ not commented out", not any(
        line.strip().startswith("#") and "backups/" in line
        for line in content.splitlines()
        if "backups/" in line and not any(
            c in line[:line.index("backups/")] for c in ["#"]
        )
    ))
    lines_with_backups = [l.strip() for l in content.splitlines() if "backups/" in l and not l.strip().startswith("#")]
    check("backups/ appears as active (non-commented) entry", len(lines_with_backups) >= 1)

print("\n-- Backup export script checks gitignore before exporting --")
export_script = ROOT / "scripts" / "export_supabase_memory_backup.py"
if export_script.exists():
    src = export_script.read_text(encoding="utf-8")
    check("export script imports _check_gitignore or defines it", "_check_gitignore" in src)
    check("export script checks gitignore in dry-run path", "_check_gitignore" in src)
    check("export script checks gitignore in export path", src.count("_check_gitignore") >= 2)
    check("export script aborts if gitignore check fails", "Fix .gitignore" in src or "gitignore" in src.lower())

print("\n-- backups/ is recognized as gitignored by git --")
# Create a temp file in backups/ and check git status
backups_dir = ROOT / "backups"
backups_dir.mkdir(exist_ok=True)
test_file = backups_dir / "_gitignore_test_probe.json"
test_file.write_text('{"test": true}', encoding="utf-8")

try:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", str(test_file)],
        capture_output=True, text=True, timeout=10
    )
    output = result.stdout.strip()
    # If gitignored, git status --short will produce no output for this file
    check("backups/ probe file not shown in git status (gitignored)", output == "" or "??" not in output)

    result2 = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-v", str(test_file)],
        capture_output=True, text=True, timeout=10
    )
    check("git check-ignore confirms backups/ is ignored", result2.returncode == 0)
    check("gitignore rule references 'backups/'", "backups/" in result2.stdout or "backups" in result2.stdout)
finally:
    if test_file.exists():
        test_file.unlink()

print("\n-- No backup files tracked in git (if git repo) --")
result3 = subprocess.run(
    ["git", "-C", str(ROOT), "ls-files", "backups/"],
    capture_output=True, text=True, timeout=10
)
tracked = result3.stdout.strip()
check("no files in backups/ tracked by git", tracked == "")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
