"""
test_memory_classification_no_supabase_writes.py
Verifies the Phase 3 generator and audit scripts contain no Supabase write calls.
Also verifies the local exec memory file wasn't modified by the audit.
"""
import sys, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent

PASS = 0; FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")

print("=== test_memory_classification_no_supabase_writes ===\n")

# ── Generator script contains no Supabase write calls ─────────────────────
print("-- generate_hermes_memory_v2_dry_run.py has no write calls --")
gen_src = (ROOT / "scripts" / "generate_hermes_memory_v2_dry_run.py").read_text()
check("no 'INSERT' in generator", "INSERT" not in gen_src.upper())
check("no 'UPSERT' in generator", "UPSERT" not in gen_src.upper())
check("no '.post(' in generator", ".post(" not in gen_src)
check("no '.patch(' in generator", ".patch(" not in gen_src)
check("_SUPABASE_WRITE_ATTEMPTED sentinel present", "_SUPABASE_WRITE_ATTEMPTED" in gen_src)
check("sentinel initialized to False", "_SUPABASE_WRITE_ATTEMPTED = False" in gen_src)

# ── Test scripts contain no write calls ───────────────────────────────────
print("\n-- Classification test scripts have no write calls --")
test_scripts = [
    "test_memory_source_map_exists.py",
    "test_memory_classification_rules.py",
    "test_memory_v2_dry_run_generator.py",
    "test_memory_classification_blocks_stale_defaults.py",
    "test_memory_classification_counts.py",
]
for script_name in test_scripts:
    p = ROOT / "scripts" / script_name
    if p.exists():
        src = p.read_text()
        # Check for actual SQL write operations (not string literals checking for INSERT)
        check(f"{script_name}: no INSERT INTO", "INSERT INTO" not in src.upper())
        check(f"{script_name}: no .post(", ".post(" not in src)
    else:
        check(f"{script_name}: exists", False)

# ── Report files are read-only metadata ────────────────────────────────────
print("\n-- Report files don't contain Supabase credentials --")
from pathlib import Path as P
memory_dir = ROOT / "docs" / "reports" / "memory"
for report_file in sorted(memory_dir.glob("*.json")):
    content = report_file.read_text(encoding="utf-8")
    check(f"{report_file.name}: no SERVICE_ROLE_KEY", "SERVICE_ROLE_KEY" not in content)
    check(f"{report_file.name}: no SUPABASE_KEY value", "eyJ" not in content)  # JWT prefix

# ── .hermes_executive_memory.json unchanged ────────────────────────────────
print("\n-- .hermes_executive_memory.json unchanged by audit --")
exec_mem = ROOT / ".hermes_executive_memory.json"
if exec_mem.exists():
    data = json.loads(exec_mem.read_text())
    check("exec memory source is empty_safe_fallback", data.get("source") == "empty_safe_fallback")
    check("exec memory monetization_priorities is empty list", data.get("monetization_priorities") == [])
    check("exec memory affiliate_campaigns is empty list", data.get("affiliate_campaigns") == [])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
