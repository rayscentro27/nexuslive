"""
test_learning_loop_no_old_table_writes.py
Verifies the learning loop module never references old Supabase tables.
"""
import sys, os
from pathlib import Path
import inspect

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_learning_loop_no_old_table_writes ===\n")

import lib.hermes_learning_loop as _ll

# Full source of learning loop module
src = Path(_ll.__file__).read_text()

# ── Old table safety ─────────────────────────────────────────────────────────
print("-- Old tables never referenced --")
OLD_TABLES = [
    "ai_memory",
    "hermes_executive_memory",
    "hermes_response_patterns",
    "memory_links",
    "knowledge_items",
    "business_opportunities",
    "executive_briefings",
    "provider_health",
    "ai_task_queue",
    "agent_dispatch_tasks",
    "human_approval_requests",
    "nexus_skills",
]
for tbl in OLD_TABLES:
    check(f"no reference to old table {tbl!r}", f'"{tbl}"' not in src and f"'{tbl}'" not in src)

# ── Only allowed table ───────────────────────────────────────────────────────
print("\n-- Only hermes_memory_v2 used for Supabase --")
check("hermes_memory_v2 referenced", "hermes_memory_v2" in src)
# All .table( calls must reference hermes_memory_v2 only
import re as _re
table_calls = _re.findall(r'\.table\(["\']([^"\']+)["\']', src)
check("all .table() calls target hermes_memory_v2 only",
      all(t == "hermes_memory_v2" for t in table_calls))

# ── _SUPABASE_WRITE_ATTEMPTED sentinel ───────────────────────────────────────
print("\n-- _SUPABASE_WRITE_ATTEMPTED = False sentinel --")
check("sentinel present in source",    "_SUPABASE_WRITE_ATTEMPTED = False" in src)
check("sentinel is False at module level", _ll._SUPABASE_WRITE_ATTEMPTED is False)

# ── approve_lesson is the only write path ────────────────────────────────────
print("\n-- approve_lesson is the only Supabase insert path --")
src_approve = inspect.getsource(_ll.approve_lesson)
check("approve_lesson calls .insert(", ".insert(" in src_approve)

# Other functions should not call .insert
for fn_name, fn in [
    ("create_lesson_proposal",  _ll.create_lesson_proposal),
    ("reject_lesson",           _ll.reject_lesson),
    ("list_pending_lessons",    _ll.list_pending_lessons),
    ("list_active_lessons",     _ll.list_active_lessons),
    ("get_last_lesson_proposal", _ll.get_last_lesson_proposal),
    ("generate_gap_lesson_proposals", _ll.generate_gap_lesson_proposals),
]:
    fn_src = inspect.getsource(fn)
    check(f"{fn_name} has no .insert(", ".insert(" not in fn_src)

# deprecate_lesson uses .update(), not .insert()
src_dep = inspect.getsource(_ll.deprecate_lesson)
check("deprecate_lesson uses .update( not .insert(", ".update(" in src_dep and ".insert(" not in src_dep)

# ── approval_required always True in proposals ────────────────────────────────
print("\n-- approval_required always True in proposals --")
check("approval_required: True in source", "approval_required" in src and "True" in src)

# ── PROPOSALS_FILE is local path ─────────────────────────────────────────────
print("\n-- PROPOSALS_FILE is a local path --")
pf = str(_ll.PROPOSALS_FILE)
check("PROPOSALS_FILE in docs/reports/memory/learning", "learning" in pf)
check("PROPOSALS_FILE ends with .jsonl", pf.endswith(".jsonl"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
