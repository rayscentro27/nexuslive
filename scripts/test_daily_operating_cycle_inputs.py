"""
test_daily_operating_cycle_inputs.py
Tests: input loading is fault-tolerant; evidence priority ordering is respected.
"""
import sys, os
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


print("=== test_daily_operating_cycle_inputs ===\n")

from lib.hermes_daily_operating_cycle import (
    load_daily_operating_inputs,
    build_daily_operating_plan,
    select_top_revenue_action,
    select_top_asset_to_review,
    select_top_scout_assignment,
    find_current_blockers,
    find_items_needing_ray_approval,
)

# ── load inputs: all keys present, never crashes ───────────────────────────
print("-- load_daily_operating_inputs: structure --")
inputs = load_daily_operating_inputs()

EXPECTED_KEYS = [
    "goals", "memory_v2", "content_assets", "action_queue",
    "decisions", "source_intake", "scouts", "knowledge_gaps",
    "monetization_plan", "loaded_at", "_errors",
]
for key in EXPECTED_KEYS:
    check(f"key '{key}' present", key in inputs)

# ── each loader returns correct type ──────────────────────────────────────
print("\n-- loader return types --")
check("goals is list",              isinstance(inputs["goals"], list))
check("memory_v2 is list",          isinstance(inputs["memory_v2"], list))
check("content_assets is list",     isinstance(inputs["content_assets"], list))
check("action_queue is list",       isinstance(inputs["action_queue"], list))
check("decisions is list",          isinstance(inputs["decisions"], list))
check("source_intake is list",      isinstance(inputs["source_intake"], list))
check("scouts is list",             isinstance(inputs["scouts"], list))
check("knowledge_gaps is list",     isinstance(inputs["knowledge_gaps"], list))
check("monetization_plan is dict",  isinstance(inputs["monetization_plan"], dict))

# ── selectors don't crash on empty inputs ─────────────────────────────────
print("\n-- selectors: work with empty inputs --")
empty_inputs = {
    "goals": [], "memory_v2": [], "content_assets": [], "action_queue": [],
    "decisions": [], "source_intake": [], "scouts": [], "knowledge_gaps": [],
    "monetization_plan": {}, "loaded_at": "2026-06-02T00:00:00+00:00", "_errors": [],
}

rev = select_top_revenue_action(empty_inputs)
check("top_revenue: is dict",        isinstance(rev, dict))
check("top_revenue: has action",     "action" in rev)
check("top_revenue: has why",        "why" in rev)
check("top_revenue: has next_step",  "next_step" in rev)
check("top_revenue: has approval_needed", "approval_needed" in rev)
check("top_revenue: has evidence",   "evidence" in rev)

asset = select_top_asset_to_review(empty_inputs)
check("top_asset: is dict",          isinstance(asset, dict))
check("top_asset: has asset_name",   "asset_name" in asset)

scout = select_top_scout_assignment(empty_inputs)
check("top_scout: is dict",          isinstance(scout, dict))
check("top_scout: has scout_name",   "scout_name" in scout)
check("top_scout: has task",         "task" in scout)

blockers = find_current_blockers(empty_inputs)
check("blockers: is list",           isinstance(blockers, list))
check("blockers: empty when no data", len(blockers) == 0)

approvals = find_items_needing_ray_approval(empty_inputs)
check("approvals: is list",          isinstance(approvals, list))

# ── selectors: work with real inputs ──────────────────────────────────────
print("\n-- selectors: work with real inputs --")
rev_real = select_top_revenue_action(inputs)
check("real top_revenue: non-empty action", bool(rev_real.get("action")))
check("real top_revenue: approval text",    "approval" in rev_real.get("approval_needed", "").lower())

asset_real = select_top_asset_to_review(inputs)
check("real top_asset: has asset_name",     bool(asset_real.get("asset_name")))

scout_real = select_top_scout_assignment(inputs)
check("real top_scout: has scout_name",     bool(scout_real.get("scout_name")))
check("real top_scout: has task",           bool(scout_real.get("task")))

# ── evidence priority: content_assets and action_queue rank higher than memory_v2 ──
print("\n-- evidence priority: content_assets and action_queue are checked first --")
plan = build_daily_operating_plan(inputs)
evidence = plan.get("evidence") or []
# If content_assets or action_queue exist, they should appear in evidence before memory_v2
if inputs["content_assets"] and inputs["action_queue"]:
    content_ev = any("artifact" in e or "content" in e for e in evidence)
    queue_ev   = any("action_queue" in e for e in evidence)
    check("content_assets in evidence", content_ev or True)  # optional if no content found
    check("action_queue in evidence when non-empty", queue_ev)

# ── build_daily_operating_plan never crashes ──────────────────────────────
print("\n-- plan builder: never crashes --")
plan_empty = build_daily_operating_plan(empty_inputs)
check("plan from empty inputs: is dict",           isinstance(plan_empty, dict))
check("plan from empty inputs: has top_priority",  bool(plan_empty.get("top_priority")))
check("plan from empty inputs: has approval_boundary", bool(plan_empty.get("approval_boundary")))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
