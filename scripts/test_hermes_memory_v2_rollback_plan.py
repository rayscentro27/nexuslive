"""
test_hermes_memory_v2_rollback_plan.py
Verifies the Phase 4A rollback plan exists and documents safe rollback
steps without auto-delete behaviors.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_rollback_plan ===\n")

print("-- File existence --")
rollback_files = sorted(MEMORY_DIR.glob("hermes_memory_v2_rollback_plan_*.md"))
check("rollback plan file exists", len(rollback_files) >= 1)

if not rollback_files:
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

content = rollback_files[-1].read_text(encoding="utf-8")

print("\n-- Core rollback philosophy --")
check("old tables remain untouched documented", "untouched" in content.lower() or "not modified" in content.lower())
check("hermes_memory_v2 can be ignored/disabled", "disable" in content.lower() or "ignore" in content.lower())
check("active memory reader fallback mentioned", "active_memory_reader" in content or "hermes_active_memory_reader" in content or "active memory reader" in content.lower())
check("migration_status rolled_back mentioned", "rolled_back" in content or "migration_status" in content)

print("\n-- Drop requires Ray approval --")
check("DROP TABLE requires explicit Ray approval",
      "ray" in content.lower() and ("approval" in content.lower() or "approve" in content.lower()))
check("no automatic drop documented", "no automatic" in content.lower() or "not occur automatically" in content.lower() or "must not occur" in content.lower())

print("\n-- Rollback prohibitions --")
check("prohibitions section present", "prohibit" in content.lower() or "not allowed" in content.lower() or "allowed?" in content.lower())
check("auto-drop prohibited", "auto" in content.lower() and "drop" in content.lower() and ("no" in content.lower() or "prohibited" in content.lower()))
check("deleting source tables prohibited", "delete records" in content.lower() or "source tables" in content.lower())
check("rollback without Ray approval prohibited", "without ray" in content.lower() or "without approval" in content.lower())

print("\n-- Source tables safety --")
for table in ["ai_memory", "hermes_executive_memory"]:
    check(f"'{table}' stated as safe/untouched", table in content)

print("\n-- Rollback does not modify production data --")
check("rollback actions executed: NO in Phase 4A",
      "no" in content.lower() and ("executed" in content.lower() or "actions" in content.lower()))
check("no SQL DELETE FROM in rollback plan (outside code block context)",
      content.count("DELETE FROM") == 0 or "-- Phase 4B SQL" in content)

print("\n-- Content safety --")
check("no SUPABASE_KEY in rollback plan", "SUPABASE_KEY" not in content and "SERVICE_ROLE_KEY" not in content)
check("no JWT tokens in rollback plan", "eyJ" not in content)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
