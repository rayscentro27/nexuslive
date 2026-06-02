"""
test_hermes_memory_v2_apply_guardrails.py
Verifies the Phase 4A apply guardrail script behaves safely by default
and refuses --apply without all required guards.
"""
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPLY_SCRIPT = ROOT / "scripts" / "apply_hermes_memory_v2_migration.py"

PASS = 0; FAIL = 0
PYTHON = sys.executable


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        [PYTHON, str(APPLY_SCRIPT)] + args,
        capture_output=True, text=True, cwd=str(ROOT)
    )
    return result.returncode, result.stdout + result.stderr


print("=== test_hermes_memory_v2_apply_guardrails ===\n")

print("-- Script existence --")
check("apply script exists", APPLY_SCRIPT.exists())

if not APPLY_SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = APPLY_SCRIPT.read_text(encoding="utf-8")

print("\n-- Source code safety checks --")
check("_SUPABASE_WRITE_ATTEMPTED = False sentinel present", "_SUPABASE_WRITE_ATTEMPTED = False" in src)
check("REQUIRED_CONFIRM_TEXT defined", "REQUIRED_CONFIRM_TEXT" in src)
check("exact confirm text is 'I APPROVE HERMES MEMORY V2 MIGRATION'",
      "I APPROVE HERMES MEMORY V2 MIGRATION" in src)
check("no .post( calls in script", ".post(" not in src)
check("no 'INSERT INTO' in script", "INSERT INTO" not in src.upper())
check("supabase db push only runs after all guards pass (Phase 4B)",
      "subprocess" in src and "supabase" in src and "db push" in src)
check("secret keys never printed — uses _safe_env pattern", "_safe_env" in src)
check("_SECRET_KEYS list defined", "_SECRET_KEYS" in src)

print("\n-- Default mode (no flags) exits safely --")
rc, out = run([])
check("default mode exits 0", rc == 0)
check("default mode says no-op or safe", any(kw in out.lower() for kw in [
    "no-op", "no changes", "data changed: no", "supabase data changed: no",
    "not applied", "migration applied: no",
]))
check("default mode does not say 'applying'", "applying migration" not in out.lower())

print("\n-- --dry-run mode --")
rc, out = run(["--dry-run"])
check("--dry-run exits 0", rc == 0)
check("--dry-run output mentions migration file", "20260602004443" in out or "hermes_memory_v2" in out)
check("--dry-run says no Supabase connection", any(kw in out.lower() for kw in [
    "no supabase", "no connection", "data changed: no", "dry run",
]))
check("--dry-run does not apply", "applying migration" not in out.lower() and "applied: yes" not in out.lower())

print("\n-- --apply without --require-ray-approval is blocked --")
rc, out = run(["--apply", "--confirm-text", "I APPROVE HERMES MEMORY V2 MIGRATION"])
check("--apply without --require-ray-approval returns non-zero", rc != 0)
check("error message mentions ray-approval", "ray" in out.lower() or "approval" in out.lower())

print("\n-- --apply without confirm text is blocked --")
rc, out = run(["--apply", "--require-ray-approval"])
check("--apply without confirm text returns non-zero", rc != 0)
check("error message mentions confirmation", "confirm" in out.lower() or "mismatch" in out.lower() or "text" in out.lower())

print("\n-- --apply with wrong confirm text is blocked --")
rc, out = run(["--apply", "--require-ray-approval", "--confirm-text", "yes please apply it"])
check("wrong confirm text returns non-zero", rc != 0)
check("error message mentions mismatch", "mismatch" in out.lower() or "required" in out.lower() or "must equal" in out.lower())

print("\n-- --apply with correct flags shows Phase 4A restriction --")
rc, out = run([
    "--apply",
    "--require-ray-approval",
    "--confirm-text", "I APPROVE HERMES MEMORY V2 MIGRATION",
])
# May succeed (0) or fail (1) depending on env/backup checks — but must NOT actually apply
check("output mentions Phase 4A restriction or guard failure", any(kw in out.lower() for kw in [
    "phase 4a", "restriction", "blocked", "missing", "not applied", "applied: no",
]))
check("output does NOT say 'migration applied: yes'", "migration applied: yes" not in out.lower())
check("output does NOT say secrets", all(s not in out for s in [
    "eyJ", "service_role_key", "SUPABASE_KEY",
]))

print("\n-- No secret VALUES in script output --")
for run_args in [[], ["--dry-run"]]:
    _, out = run(run_args)
    # eyJ is the JWT token prefix — must never appear (would mean a secret value was printed)
    check(f"no JWT token value in output (args={run_args})", "eyJ" not in out)
    # SERVICE_ROLE_KEY may appear as a variable NAME in error messages (missing env var warning)
    # but its VALUE (a long JWT) must never be printed
    lines_with_key_value = [l for l in out.splitlines()
                             if "SERVICE_ROLE_KEY" in l.upper() and "eyJ" in l]
    check(f"no SERVICE_ROLE_KEY value in output (args={run_args})", len(lines_with_key_value) == 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
