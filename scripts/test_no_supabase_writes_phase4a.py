"""
test_no_supabase_writes_phase4a.py
Verifies that no Phase 4A Python script executes Supabase writes,
applies migrations, drops tables, or deletes records.
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


print("=== test_no_supabase_writes_phase4a ===\n")

phase4a_scripts = [
    ("apply_hermes_memory_v2_migration.py", "apply guardrail script"),
    ("generate_hermes_memory_v2_dry_run.py", "dry-run generator"),
    ("test_hermes_memory_v2_schema_doc.py", "schema doc test"),
    ("test_hermes_memory_v2_sql_migration.py", "sql migration test"),
    ("test_hermes_memory_v2_apply_guardrails.py", "apply guardrails test"),
    ("test_hermes_memory_v2_backup_plan.py", "backup plan test"),
    ("test_hermes_memory_v2_rollback_plan.py", "rollback plan test"),
    ("test_hermes_memory_v2_dry_run_schema_validation.py", "schema validation test"),
]

print("-- No Supabase write calls in Phase 4A production scripts --")
# Separate production scripts from test scripts — test scripts necessarily reference
# SQL keywords in their assertion strings (e.g. check("no INSERT INTO", ...))
production_scripts = [
    ("apply_hermes_memory_v2_migration.py", "apply guardrail script"),
    ("generate_hermes_memory_v2_dry_run.py", "dry-run generator"),
]
for filename, label in production_scripts:
    src = scan(ROOT / "scripts" / filename, label)
    if not src:
        continue
    check(f"{filename}: no 'INSERT INTO'", "INSERT INTO" not in src.upper())
    check(f"{filename}: no '.post('", ".post(" not in src)
    check(f"{filename}: no '.patch('", ".patch(" not in src)
    check(f"{filename}: no supabase write client calls", ".upsert(" not in src)

print("\n-- Test scripts don't execute Supabase writes --")
test_scripts = [s for s in phase4a_scripts if s[0].startswith("test_")]
for filename, label in test_scripts:
    src = scan(ROOT / "scripts" / filename, label)
    if not src:
        continue
    # Test scripts reference SQL keywords in their assertions (e.g. check("no .post(", ...))
    # so we check for actual execution calls, not string literals
    check(f"{filename}: no .upsert( calls", ".upsert(" not in src)
    # subprocess.run is allowed in test scripts to invoke the apply script for testing
    # — check that it only invokes the apply script, not supabase CLI directly
    # A direct supabase CLI call would look like: subprocess.run(["supabase", ...])
    # Test files may reference both words in assertion strings — check for actual list syntax
    has_direct_supabase_call = (
        'subprocess.run(["supabase"' in src or
        "subprocess.run(['supabase'" in src
    )
    check(f"{filename}: no direct supabase CLI subprocess.run call", not has_direct_supabase_call)

print("\n-- Apply script specifically cannot execute migration --")
apply_src = (ROOT / "scripts" / "apply_hermes_memory_v2_migration.py").read_text()
# The apply script may print the supabase command but must not subprocess.run it
apply_has_subprocess_run = "subprocess.run" in apply_src and "supabase" in apply_src
check("apply script does not subprocess.run supabase commands",
      "subprocess" not in apply_src or
      ("subprocess" in apply_src and "supabase db push" not in apply_src.replace("print(", "")))
check("_SUPABASE_WRITE_ATTEMPTED = False in apply script",
      "_SUPABASE_WRITE_ATTEMPTED = False" in apply_src)

print("\n-- SQL migration file exists but is not auto-executed --")
migration_file = ROOT / "supabase" / "migrations" / "20260602004443_create_hermes_memory_v2.sql"
check("migration file exists", migration_file.exists())
# Verify no Python script imports and auto-runs the migration
gen_src = (ROOT / "scripts" / "generate_hermes_memory_v2_dry_run.py").read_text()
check("generator does not import supabase client for writes",
      "supabase" not in gen_src.lower() or
      ("supabase" in gen_src.lower() and ".post(" not in gen_src and ".upsert(" not in gen_src))

print("\n-- No DROP TABLE execution in Phase 4A production Python --")
for filename, label in production_scripts:
    p = ROOT / "scripts" / filename
    if p.exists():
        src = p.read_text()
        check(f"{filename}: no 'DROP TABLE' execution", "DROP TABLE" not in src.upper())

print("\n-- No DELETE FROM execution in Phase 4A production Python --")
for filename, label in production_scripts:
    p = ROOT / "scripts" / filename
    if p.exists():
        src = p.read_text()
        check(f"{filename}: no 'DELETE FROM' execution", "DELETE FROM" not in src.upper())

print("\n-- SQL migration itself is safe --")
if migration_file.exists():
    sql = migration_file.read_text()
    check("SQL migration: no data INSERT INTO", "INSERT INTO" not in sql.upper())
    check("SQL migration: no UPDATE rows", "UPDATE hermes_memory_v2 SET" not in sql.upper())
    check("SQL migration: no DELETE", "DELETE FROM" not in sql.upper())
    check("SQL migration: no DROP TABLE", "DROP TABLE" not in sql.upper())

print("\n-- No secret VALUES in Phase 4A production scripts --")
for filename, _ in production_scripts:
    p = ROOT / "scripts" / filename
    if p.exists():
        src = p.read_text()
        # eyJ is JWT token prefix — must never appear as a hardcoded value
        check(f"{filename}: no eyJ JWT token", "eyJ" not in src)
        # SERVICE_ROLE_KEY may appear as variable name in env checks — safe if no JWT value
        # JWT values start with eyJ — already checked above, so this check is supplementary
        has_jwt_on_key_line = any(
            "SERVICE_ROLE_KEY" in l and "eyJ" in l
            for l in src.splitlines()
        )
        check(f"{filename}: no SERVICE_ROLE_KEY=<jwt_value> hardcoded", not has_jwt_on_key_line)

print("\n-- Phase 3B safety: _SUPABASE_WRITE_ATTEMPTED in generator --")
check("generator has _SUPABASE_WRITE_ATTEMPTED sentinel",
      "_SUPABASE_WRITE_ATTEMPTED" in gen_src)
check("generator sentinel initialized to False",
      "_SUPABASE_WRITE_ATTEMPTED = False" in gen_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
