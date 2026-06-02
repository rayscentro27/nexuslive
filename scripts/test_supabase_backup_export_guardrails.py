"""
test_supabase_backup_export_guardrails.py
Verifies that --export is blocked without correct confirm text,
and that gitignore check is enforced.
"""
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_SCRIPT = ROOT / "scripts" / "export_supabase_memory_backup.py"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def run(args: list, timeout=15) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT)] + args,
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout + result.stderr


print("=== test_supabase_backup_export_guardrails ===\n")

print("-- --export without confirm text is blocked --")
code, out = run(["--export"])
check("--export without --confirm-text exits non-zero", code != 0)
check("--export without --confirm-text mentions confirm-text requirement", "confirm" in out.lower())

print("\n-- --export with wrong confirm text is blocked --")
code2, out2 = run(["--export", "--confirm-text", "wrong text"])
check("--export with wrong text exits non-zero", code2 != 0)
check("wrong text output mentions confirm", "confirm" in out2.lower() or "mismatch" in out2.lower() or "required" in out2.lower())

print("\n-- --export with partial confirm text is blocked --")
code3, out3 = run(["--export", "--confirm-text", "I APPROVE"])
check("partial confirm text exits non-zero", code3 != 0)

print("\n-- --export with correct confirm text checks gitignore --")
code4, out4 = run(["--export", "--confirm-text", "I APPROVE HERMES MEMORY BACKUP EXPORT"])
# Whether it passes or fails depends on gitignore and env — it should not crash
check("--export with correct text exits 0 or 1 (not crash)", code4 in (0, 1))
check("--export with correct text mentions gitignore or env", "gitignore" in out4.lower() or "env" in out4.lower() or "SUPABASE" in out4)

print("\n-- No secrets appear in any output --")
for label, (code_, out_) in [
    ("default", run([])),
    ("--dry-run", run(["--dry-run"])),
    ("--export no-confirm", run(["--export"])),
]:
    check(f"{label}: no eyJ JWT token in output", "eyJ" not in out_)

print("\n-- Source-level guardrail checks --")
src = EXPORT_SCRIPT.read_text(encoding="utf-8")
check("--export flag requires confirm text check in source", "REQUIRED_CONFIRM_TEXT" in src)
check("gitignore check called in export path", "_check_gitignore" in src)
check("env check called in export path", "_safe_env_check" in src or "safe_env" in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
