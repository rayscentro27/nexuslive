"""
test_hermes_memory_v2_backup_plan.py
Verifies the Phase 4A backup plan document exists and contains all
required tables, local files, and checklist items.
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


print("=== test_hermes_memory_v2_backup_plan ===\n")

print("-- File existence --")
backup_files = sorted(MEMORY_DIR.glob("hermes_memory_v2_backup_plan_*.md"))
check("backup plan file exists", len(backup_files) >= 1)

if not backup_files:
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

content = backup_files[-1].read_text(encoding="utf-8")

print("\n-- Required tables documented --")
required_tables = [
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
for table in required_tables:
    check(f"table '{table}' in backup plan", table in content)

print("\n-- Required local files documented --")
required_local_files = [
    ".hermes_executive_memory.json",
    ".hermes_ops_memory.json",
    "hermes_action_queue.jsonl",
    "hermes_decision_log.jsonl",
    "hermes_conversation_context.json",
]
for lf in required_local_files:
    check(f"local file '{lf}' in backup plan", lf in content)

print("\n-- Sensitive data warnings --")
check("mentions gitignore", "gitignore" in content.lower() or ".gitignore" in content)
check("sensitive data warning present", "sensitive" in content.lower() or "do not commit" in content.lower())
check("backups/ directory mentioned", "backups/" in content or "backups" in content)

print("\n-- Checklist items --")
check("backup verification checklist present",
      "verification checklist" in content.lower() or "verify" in content.lower())
check("restore/rollback checklist present",
      "rollback" in content.lower() or "restore" in content.lower())

print("\n-- Phase 4A constraint --")
check("no actual backups created in Phase 4A",
      "no actual backups" in content.lower() or "plan only" in content.lower() or
      "not created" in content.lower() or "phase 4a" in content.lower())

print("\n-- Content safety --")
check("no SUPABASE_KEY in backup plan", "SUPABASE_KEY" not in content and "SERVICE_ROLE_KEY" not in content)
check("no JWT tokens in backup plan", "eyJ" not in content)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
