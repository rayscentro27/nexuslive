"""
test_phase4a5_no_supabase_writes.py
Verifies that no Phase 4A.5 script attempts Supabase writes,
drops tables, deletes records, or exposes secrets.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def scan(path: Path, label: str) -> str:
    if not path.exists():
        check(f"{label} exists", False)
        return ""
    check(f"{label} exists", True)
    return path.read_text(encoding="utf-8")


print("=== test_phase4a5_no_supabase_writes ===\n")

phase4a5_production_scripts = [
    ("export_supabase_memory_backup.py", "backup export script"),
    ("apply_hermes_memory_v2_migration.py", "apply guardrail script"),
]

print("-- Safety sentinels present --")
for filename, label in phase4a5_production_scripts:
    src = scan(ROOT / "scripts" / filename, label)
    if not src:
        continue
    check(f"{filename}: _SUPABASE_WRITE_ATTEMPTED = False sentinel", "_SUPABASE_WRITE_ATTEMPTED = False" in src)
    check(f"{filename}: sentinel never set to True", "_SUPABASE_WRITE_ATTEMPTED = True" not in src)

print("\n-- No Supabase write calls in production scripts --")
for filename, label in phase4a5_production_scripts:
    p = ROOT / "scripts" / filename
    if not p.exists():
        continue
    src = p.read_text(encoding="utf-8")
    check(f"{filename}: no .upsert( call", ".upsert(" not in src)
    check(f"{filename}: no INSERT INTO execution", "INSERT INTO" not in src.upper() or
          all("INSERT INTO" not in line.upper() for line in src.splitlines()
              if not line.strip().startswith('"') and not line.strip().startswith("'")))

print("\n-- No DROP TABLE in production scripts --")
for filename, _ in phase4a5_production_scripts:
    p = ROOT / "scripts" / filename
    if p.exists():
        src = p.read_text(encoding="utf-8")
        check(f"{filename}: no DROP TABLE", "DROP TABLE" not in src.upper())

print("\n-- No DELETE FROM in production scripts --")
for filename, _ in phase4a5_production_scripts:
    p = ROOT / "scripts" / filename
    if p.exists():
        src = p.read_text(encoding="utf-8")
        check(f"{filename}: no DELETE FROM", "DELETE FROM" not in src.upper())

print("\n-- No hardcoded secrets in production scripts --")
for filename, _ in phase4a5_production_scripts:
    p = ROOT / "scripts" / filename
    if p.exists():
        src = p.read_text(encoding="utf-8")
        check(f"{filename}: no eyJ JWT token", "eyJ" not in src)
        has_jwt_on_key_line = any(
            "SERVICE_ROLE_KEY" in line and "eyJ" in line
            for line in src.splitlines()
        )
        check(f"{filename}: no hardcoded SERVICE_ROLE_KEY=<jwt>", not has_jwt_on_key_line)

print("\n-- Export script does not subprocess.run supabase CLI --")
export_src = (ROOT / "scripts" / "export_supabase_memory_backup.py").read_text(encoding="utf-8")
has_supabase_subprocess = (
    'subprocess.run(["supabase"' in export_src or
    "subprocess.run(['supabase'" in export_src
)
check("export script has no direct supabase CLI subprocess.run", not has_supabase_subprocess)

print("\n-- Apply script does not subprocess.run supabase db push --")
apply_src = (ROOT / "scripts" / "apply_hermes_memory_v2_migration.py").read_text(encoding="utf-8")
apply_runs_push = (
    "supabase db push" in apply_src and
    "subprocess.run" in apply_src and
    "print(" not in apply_src.split("supabase db push")[0][-50:]
)
check("apply script does not execute supabase db push", "supabase db push" not in apply_src or
      "subprocess" not in apply_src or
      "supabase db push" not in apply_src.replace("print(", ""))

print("\n-- Phase 4A sentinel still intact after 4A.5 modifications --")
check("apply script _SUPABASE_WRITE_ATTEMPTED still False", "_SUPABASE_WRITE_ATTEMPTED = False" in apply_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
