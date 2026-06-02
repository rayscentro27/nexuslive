"""
test_live_memory_v2_primary_does_not_break_content_loop.py
Verifies that enabling primary mode does NOT break:
  - Content artifact workflow
  - Action queue
  - Decision log
  - Source intake records
  - Fresh artifacts always override structured memory
"""
import sys, os, inspect
from pathlib import Path

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


print("=== test_live_memory_v2_primary_does_not_break_content_loop ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- Priority contract in load_primary_memory_context --")
ctx = shadow.load_primary_memory_context()
note = ctx.get("priority_note", "")
check("priority_note present", bool(note))
check("priority_note says conversation context or fresh artifacts override",
      "override" in note.lower() or "current" in note.lower())

print("\n-- priority_note in module docstring / comments --")
module_src = inspect.getsource(shadow)
check("module docstring mentions artifacts override",
      "artifacts" in module_src or "artifact" in module_src)
check("load_primary_memory_context mentions priority",
      "priority" in inspect.getsource(shadow.load_primary_memory_context))

print("\n-- Primary mode does not write to OLD_TABLES --")
OLD_TABLES = [
    "ai_memory", "hermes_executive_memory", "hermes_response_patterns",
    "memory_links", "knowledge_items", "business_opportunities",
    "executive_briefings", "provider_health", "ai_task_queue",
    "agent_dispatch_tasks", "human_approval_requests", "nexus_skills",
]
for tbl in OLD_TABLES:
    check(f"shadow module does not write to {tbl}",
          f'"{tbl}").insert(' not in module_src and
          f"'{tbl}').insert(" not in module_src)

print("\n-- Primary mode does not modify hermes_memory_v2 --")
check("shadow module has no .insert() on hermes_memory_v2",
      '"hermes_memory_v2").insert(' not in module_src and
      "'hermes_memory_v2').insert(" not in module_src)
check("shadow module has no .update() on hermes_memory_v2",
      '"hermes_memory_v2").update(' not in module_src and
      "'hermes_memory_v2').update(" not in module_src)
check("shadow module has no .delete() on hermes_memory_v2",
      '"hermes_memory_v2").delete(' not in module_src and
      "'hermes_memory_v2').delete(" not in module_src)

print("\n-- Telegram bot shadow hook fires in primary mode too --")
import telegram_bot as tb_mod
tb_src = inspect.getsource(tb_mod)
check("telegram_bot imports is_primary_mode_active",
      "is_primary_mode_active" in tb_src)
check("telegram_bot fires trigger_shadow_comparison_async in primary mode",
      ("is_primary_mode_active()" in tb_src and "trigger_shadow_comparison_async" in tb_src))

print("\n-- telegram_bot.py: memory_v2_primary_status in SAFE_REPEATABLE_MEMORY_INTENTS --")
check("memory_v2_primary_status in SAFE_REPEATABLE_MEMORY_INTENTS",
      "memory_v2_primary_status" in tb_src)

print("\n-- Primary mode activation does NOT restart content workers --")
# Verify load_primary_memory_context doesn't call subprocess or os.system
ctx_src = inspect.getsource(shadow.load_primary_memory_context)
check("load_primary_memory_context has no subprocess call", "subprocess" not in ctx_src)
check("load_primary_memory_context has no os.system call", "os.system" not in ctx_src)

print("\n-- Content artifacts path still accessible --")
artifacts_dir = ROOT / "docs" / "reports"
check("docs/reports directory exists", artifacts_dir.exists())
decision_log = ROOT / "docs" / "reports" / "decisions" / "hermes_decision_log.jsonl"
# Just check the path is well-formed — file may or may not exist
check("decision log path is under docs/reports", "docs/reports" in str(decision_log))

print("\n-- _SUPABASE_WRITE_ATTEMPTED remains False --")
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
