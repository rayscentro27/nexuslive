"""
test_task_dispatch_skill_classification.py
Verifies Phase 3B task queue, agent dispatch, and nexus skills classification rules.
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_memory_freshness import (
    classify_task_record,
    classify_nexus_skill,
    classify_record,
    TASK_MAX_AGE_H,
    DISPATCH_MAX_AGE_H,
    _ACTIVE_TASK_STATUSES,
    _ACTIVE_DISPATCH_STATUSES,
    _ACTIVE_SKILL_STATUSES,
    _INACTIVE_SKILL_STATUSES,
)

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def ts_ago_hours(h: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=h)
    return dt.isoformat()


print("=== test_task_dispatch_skill_classification ===\n")

# ── Constants ─────────────────────────────────────────────────────────────────
print("-- Constants --")
check("TASK_MAX_AGE_H == 24", TASK_MAX_AGE_H == 24)
check("DISPATCH_MAX_AGE_H == 24", DISPATCH_MAX_AGE_H == 24)
check("'queued' in active task statuses", "queued" in _ACTIVE_TASK_STATUSES)
check("'running' in active task statuses", "running" in _ACTIVE_TASK_STATUSES)
check("'in_progress' in active task statuses", "in_progress" in _ACTIVE_TASK_STATUSES)
check("'pending' in active task statuses", "pending" in _ACTIVE_TASK_STATUSES)
check("'assigned' in active task statuses", "assigned" in _ACTIVE_TASK_STATUSES)
check("'active' in dispatch statuses", "active" in _ACTIVE_DISPATCH_STATUSES)
check("'enabled' in skill statuses", "enabled" in _ACTIVE_SKILL_STATUSES)
check("'disabled' in inactive skill statuses", "disabled" in _INACTIVE_SKILL_STATUSES)

# ── ai_task_queue: active + fresh ────────────────────────────────────────────
print("\n-- ai_task_queue: active + fresh --")
for status in ["queued", "running", "assigned", "pending", "in_progress"]:
    rec = {"status": status, "updated_at": ts_ago_hours(1)}
    check(f"fresh '{status}' → active_live_answer",
          classify_task_record(rec) == "active_live_answer")

# ── ai_task_queue: completed statuses ─────────────────────────────────────────
print("\n-- ai_task_queue: completed statuses → historical --")
for status in ["completed", "done", "succeeded", "cancelled", "failed", "error"]:
    rec = {"status": status, "updated_at": ts_ago_hours(1)}
    check(f"'{status}' → historical_only",
          classify_task_record(rec) == "historical_only")

# ── ai_task_queue: stale pending ──────────────────────────────────────────────
print("\n-- ai_task_queue: stale pending (25h old) --")
stale_pending = {"status": "pending", "updated_at": ts_ago_hours(25)}
check("stale pending → historical_only", classify_task_record(stale_pending) == "historical_only")

stale_queued = {"status": "queued", "updated_at": ts_ago_hours(30)}
check("stale queued → historical_only", classify_task_record(stale_queued) == "historical_only")

# ── ai_task_queue: no timestamp ───────────────────────────────────────────────
print("\n-- ai_task_queue: no timestamp --")
no_ts = {"status": "pending"}
check("no timestamp → needs_review", classify_task_record(no_ts) == "needs_review")

# ── agent_dispatch_tasks: active statuses ────────────────────────────────────
print("\n-- agent_dispatch_tasks: active + fresh --")
for status in ["active", "pending", "running", "assigned", "in_progress"]:
    rec = {"status": status, "updated_at": ts_ago_hours(1)}
    check(f"dispatch fresh '{status}' → active_live_answer",
          classify_task_record(rec, "agent_dispatch_tasks") == "active_live_answer")

print("\n-- agent_dispatch_tasks: stale --")
stale_dispatch = {"status": "active", "updated_at": ts_ago_hours(25)}
check("stale dispatch 'active' → historical_only",
      classify_task_record(stale_dispatch, "agent_dispatch_tasks") == "historical_only")

# ── nexus_skills ──────────────────────────────────────────────────────────────
print("\n-- nexus_skills: enabled/active/installed --")
for status in ["enabled", "active", "installed"]:
    check(f"skill '{status}' → active_live_answer",
          classify_nexus_skill({"status": status}) == "active_live_answer")

check("skill status=true → active", classify_nexus_skill({"status": "true"}) == "active_live_answer")
check("skill enabled=1 → active", classify_nexus_skill({"enabled": "1"}) == "active_live_answer")

print("\n-- nexus_skills: disabled/deprecated/removed --")
for status in ["disabled", "deprecated", "removed"]:
    check(f"skill '{status}' → historical_only",
          classify_nexus_skill({"status": status}) == "historical_only")

check("skill status=false → historical", classify_nexus_skill({"status": "false"}) == "historical_only")

print("\n-- nexus_skills: unknown status --")
check("skill status=unknown → needs_review",
      classify_nexus_skill({"status": "unknown"}) == "needs_review")
check("skill no status → needs_review", classify_nexus_skill({}) == "needs_review")

# ── classify_record dispatcher ───────────────────────────────────────────────
print("\n-- classify_record() dispatcher --")
fresh_task = {"status": "running", "updated_at": ts_ago_hours(1)}
check("classify_record('ai_task_queue', ...) → active_live_answer",
      classify_record("ai_task_queue", fresh_task) == "active_live_answer")

dispatch_rec = {"status": "active", "updated_at": ts_ago_hours(1)}
check("classify_record('agent_dispatch_tasks', ...) → active_live_answer",
      classify_record("agent_dispatch_tasks", dispatch_rec) == "active_live_answer")

skill_rec = {"status": "enabled"}
check("classify_record('nexus_skills', ...) → active_live_answer",
      classify_record("nexus_skills", skill_rec) == "active_live_answer")

unknown_table = {"status": "something"}
check("classify_record('unknown_table', ...) → needs_review",
      classify_record("unknown_table", unknown_table) == "needs_review")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
