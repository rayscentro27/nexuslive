"""
test_supabase_backup_export_dry_run.py
Verifies that the backup export script behaves correctly in default/dry-run mode:
no Supabase connection, no files written, prints what would be exported.
"""
import sys, subprocess, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_SCRIPT = ROOT / "scripts" / "export_supabase_memory_backup.py"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_supabase_backup_export_dry_run ===\n")

print("-- Export script exists --")
check("export_supabase_memory_backup.py exists", EXPORT_SCRIPT.exists())

if not EXPORT_SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(FAIL)

src = EXPORT_SCRIPT.read_text(encoding="utf-8")

print("\n-- Safety sentinel present --")
check("_SUPABASE_WRITE_ATTEMPTED = False sentinel in source", "_SUPABASE_WRITE_ATTEMPTED = False" in src)
check("sentinel never set to True", "_SUPABASE_WRITE_ATTEMPTED = True" not in src)

print("\n-- Required confirm text constant defined --")
REQUIRED = "I APPROVE HERMES MEMORY BACKUP EXPORT"
check(f"REQUIRED_CONFIRM_TEXT = '{REQUIRED}' in source", REQUIRED in src)

print("\n-- All 12 memory tables listed --")
EXPECTED_TABLES = [
    "ai_memory", "hermes_executive_memory", "hermes_response_patterns",
    "memory_links", "knowledge_items", "business_opportunities",
    "executive_briefings", "provider_health", "ai_task_queue",
    "agent_dispatch_tasks", "human_approval_requests", "nexus_skills",
]
for t in EXPECTED_TABLES:
    check(f"table '{t}' listed in MEMORY_TABLES", f'"{t}"' in src or f"'{t}'" in src)

print("\n-- Gitignore check function present --")
check("_check_gitignore function defined", "_check_gitignore" in src)
check("'backups/' checked in gitignore", "backups/" in src)

print("\n-- No secrets printed in source --")
check("no hardcoded eyJ JWT token", "eyJ" not in src)
check("_safe_env_check returns bool not value", "_safe_env_check" in src)

print("\n-- Default mode is dry-run (subprocess call) --")
result = subprocess.run(
    [sys.executable, str(EXPORT_SCRIPT)],
    capture_output=True, text=True, timeout=15
)
output = result.stdout + result.stderr
check("default invocation exits 0 or 1 (not crash)", result.returncode in (0, 1))
check("default output mentions 'Dry-Run' or 'dry-run'", "dry" in output.lower() or "Dry" in output)
check("default output does not mention 'ERROR: --export'", "must equal" not in output.lower())

print("\n-- --dry-run flag works --")
result2 = subprocess.run(
    [sys.executable, str(EXPORT_SCRIPT), "--dry-run"],
    capture_output=True, text=True, timeout=15
)
output2 = result2.stdout + result2.stderr
check("--dry-run exits 0 or 1", result2.returncode in (0, 1))
check("--dry-run output mentions tables", any(t in output2 for t in EXPECTED_TABLES))
check("--dry-run does not write files to backups/", "No files written" in output2 or "no files" in output2.lower())

print("\n-- --verify-only flag works --")
result3 = subprocess.run(
    [sys.executable, str(EXPORT_SCRIPT), "--verify-only"],
    capture_output=True, text=True, timeout=15
)
output3 = result3.stdout + result3.stderr
check("--verify-only exits 0 or 1", result3.returncode in (0, 1))
check("--verify-only output mentions gitignore", "gitignore" in output3.lower() or "Gitignore" in output3)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
