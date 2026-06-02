"""
test_phase4d_no_supabase_writes.py
Verifies that no Phase 4D module attempts Supabase writes. Checks sentinels,
source code patterns, and that all scripts set _SUPABASE_WRITE_ATTEMPTED=False.
"""
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_phase4d_no_supabase_writes ===\n")

print("-- hermes_memory_v2_reader write guard --")
import lib.hermes_memory_v2_reader as v2
check("_SUPABASE_WRITE_ATTEMPTED is False (module attr)",
      v2._SUPABASE_WRITE_ATTEMPTED is False)

src_v2 = inspect.getsource(v2)
check("source does not call .insert(", ".insert(" not in src_v2)
check("source does not call .upsert(", ".upsert(" not in src_v2)
check("source does not call .update(", ".update(" not in src_v2 or
      "_SUPABASE_WRITE_ATTEMPTED" in src_v2)
check("source does not call .delete(", ".delete(" not in src_v2)
check("source contains _SUPABASE_WRITE_ATTEMPTED sentinel",
      "_SUPABASE_WRITE_ATTEMPTED" in src_v2)
check("no hermes_memory_v2 table writes in source",
      "hermes_memory_v2" not in src_v2 or
      all(f"hermes_memory_v2\").{op}(" not in src_v2
          for op in ["insert", "upsert", "update", "delete"]))

print("\n-- batch2 dry-run write guard --")
import scripts.prepare_hermes_memory_v2_batch2_dry_run as batch2
check("_SUPABASE_WRITE_ATTEMPTED is False", batch2._SUPABASE_WRITE_ATTEMPTED is False)

src_b2 = inspect.getsource(batch2)
check("source contains _SUPABASE_WRITE_ATTEMPTED sentinel",
      "_SUPABASE_WRITE_ATTEMPTED" in src_b2)
check("source does not call .insert( unguarded",
      ".insert(" not in src_b2 or "_SUPABASE_WRITE_ATTEMPTED" in src_b2)

print("\n-- compare_hermes_memory_readers write guard --")
import scripts.compare_hermes_memory_readers as cmp_script
check("_SUPABASE_WRITE_ATTEMPTED is False",
      cmp_script._SUPABASE_WRITE_ATTEMPTED is False)

src_cmp = inspect.getsource(cmp_script)
check("no supabase .insert( in compare script",
      not any(f'"{t}").insert(' in src_cmp or f"'{t}').insert(" in src_cmp
              for t in ["hermes_memory_v2", "ai_memory", "hermes_executive_memory"]))
check("no .upsert( in compare script", ".upsert(" not in src_cmp)
check("no .delete( in compare script", ".delete(" not in src_cmp)

print("\n-- router handlers do not write to Supabase --")
from hermes_command_router import router
src_router = inspect.getsource(router)
v2_handler_names = ["_plain_memory_v2_preview", "_plain_memory_v2_compare",
                    "_plain_memory_v2_rules", "_plain_memory_v2_status"]
for fn_name in v2_handler_names:
    fn = getattr(router, fn_name, None)
    check(f"function '{fn_name}' exists", fn is not None)
    if fn:
        fn_src = inspect.getsource(fn)
        check(f"'{fn_name}' does not call .insert(", ".insert(" not in fn_src)
        check(f"'{fn_name}' does not call .upsert(", ".upsert(" not in fn_src)

print("\n-- OLD_TABLES not written from Phase 4D modules --")
OLD_TABLES = [
    "ai_memory", "hermes_executive_memory", "hermes_response_patterns",
    "memory_links", "knowledge_items", "business_opportunities",
    "executive_briefings", "provider_health", "ai_task_queue",
    "agent_dispatch_tasks", "human_approval_requests", "nexus_skills",
]
for table in OLD_TABLES:
    write_pattern_v2 = any(
        f'"{table}").{op}(' in src_v2
        for op in ["insert", "upsert", "update", "delete"]
    )
    check(f"v2 reader does not write to '{table}'", not write_pattern_v2)

print("\n-- No backfill apply flag set --")
check("batch2 _SUPABASE_WRITE_ATTEMPTED remains False after import",
      batch2._SUPABASE_WRITE_ATTEMPTED is False)
check("v2 reader _SUPABASE_WRITE_ATTEMPTED remains False after import",
      v2._SUPABASE_WRITE_ATTEMPTED is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
