"""
test_backfill_hermes_memory_v2_no_old_table_writes.py
Verifies backfill script never writes to old memory tables.
"""
import sys, ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "backfill_hermes_memory_v2.py"

OLD_TABLES = [
    "ai_memory", "hermes_executive_memory", "hermes_response_patterns",
    "memory_links", "knowledge_items", "business_opportunities",
    "executive_briefings", "provider_health", "ai_task_queue",
    "agent_dispatch_tasks", "human_approval_requests", "nexus_skills",
]

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_backfill_hermes_memory_v2_no_old_table_writes ===\n")

check("backfill_hermes_memory_v2.py exists", SCRIPT.exists())
if not SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = SCRIPT.read_text(encoding="utf-8")

print("-- OLD_TABLES defined --")
check("OLD_TABLES constant defined", "OLD_TABLES" in src)
for t in OLD_TABLES:
    check(f"'{t}' in OLD_TABLES", t in src)

print("\n-- Only hermes_memory_v2 targeted for insert --")
check("insert only targets hermes_memory_v2",
      'table("hermes_memory_v2").insert' in src)
# Verify no insert calls target old tables
for t in OLD_TABLES:
    check(f"no insert into {t}",
          f'table("{t}").insert' not in src and f"table('{t}').insert" not in src)

print("\n-- No upsert or update calls --")
check("no .upsert() calls", ".upsert(" not in src)
check("no .update() calls", ".update(" not in src)
check("no .delete() calls", ".delete(" not in src)

print("\n-- Old table safety check in run_apply --")
check("JSONL path checked against OLD_TABLES before insert",
      "OLD_TABLES" in src and "jsonl_path" in src and "SAFETY ERROR" in src)

print("\n-- _SUPABASE_WRITE_ATTEMPTED sentinel --")
check("_SUPABASE_WRITE_ATTEMPTED = False present", "_SUPABASE_WRITE_ATTEMPTED = False" in src)
check("_SUPABASE_WRITE_ATTEMPTED never set True", "_SUPABASE_WRITE_ATTEMPTED = True" not in src)

print("\n-- Writes target field in apply result --")
check("writes_target field set to 'hermes_memory_v2 only'",
      "hermes_memory_v2 only" in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
