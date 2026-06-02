"""
test_daily_operating_cycle_plan.py
Tests: build_daily_operating_plan and format_daily_operating_plan produce TODAY'S NEXUS PLAN.
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


print("=== test_daily_operating_cycle_plan ===\n")

from lib.hermes_daily_operating_cycle import (
    load_daily_operating_inputs,
    build_daily_operating_plan,
    format_daily_operating_plan,
)

# ── load_daily_operating_inputs ────────────────────────────────────────────
print("-- load_daily_operating_inputs --")
inputs = load_daily_operating_inputs()
check("inputs is dict",                  isinstance(inputs, dict))
check("has loaded_at",                   "loaded_at" in inputs)
check("has goals key",                   "goals" in inputs)
check("has memory_v2 key",               "memory_v2" in inputs)
check("has content_assets key",          "content_assets" in inputs)
check("has action_queue key",            "action_queue" in inputs)
check("has decisions key",               "decisions" in inputs)
check("has source_intake key",           "source_intake" in inputs)
check("has scouts key",                  "scouts" in inputs)
check("has knowledge_gaps key",          "knowledge_gaps" in inputs)
check("has monetization_plan key",       "monetization_plan" in inputs)
check("has _errors key",                 "_errors" in inputs)
check("_errors is list",                 isinstance(inputs.get("_errors"), list))
check("goals is list",                   isinstance(inputs.get("goals"), list))
check("content_assets is list",          isinstance(inputs.get("content_assets"), list))
check("action_queue is list",            isinstance(inputs.get("action_queue"), list))
check("never crashes",                   True)  # if we got here, it didn't crash

# ── build_daily_operating_plan ─────────────────────────────────────────────
print("\n-- build_daily_operating_plan --")
plan = build_daily_operating_plan(inputs)
check("plan is dict",                    isinstance(plan, dict))
check("plan has date",                   bool(plan.get("date")))
check("plan has top_priority",           "top_priority" in plan)
check("plan has top_priority_why",       "top_priority_why" in plan)
check("plan has top_revenue",            isinstance(plan.get("top_revenue"), dict))
check("plan has top_asset",              isinstance(plan.get("top_asset"), dict))
check("plan has top_scout",              isinstance(plan.get("top_scout"), dict))
check("plan has blockers",               isinstance(plan.get("blockers"), list))
check("plan has approval_items",         isinstance(plan.get("approval_items"), list))
check("plan has safe_next_actions",      isinstance(plan.get("safe_next_actions"), list))
check("plan has evidence",               isinstance(plan.get("evidence"), list))
check("plan has approval_boundary",      bool(plan.get("approval_boundary")))

# ── format_daily_operating_plan ────────────────────────────────────────────
print("\n-- format_daily_operating_plan --")
formatted = format_daily_operating_plan(plan)
check("formatted is non-empty str",              bool(formatted))
check("starts with TODAY'S NEXUS PLAN",          formatted.startswith("TODAY'S NEXUS PLAN"))
check("contains date",                           plan["date"] in formatted)
check("contains 'Top priority'",                 "Top priority" in formatted)
check("contains '1. Money move'",                "1. Money move" in formatted)
check("contains '2. Asset to review'",           "2. Asset to review" in formatted)
check("contains '3. Scout assignment'",          "3. Scout assignment" in formatted)
check("contains '4. Blockers'",                  "4. Blockers" in formatted)
check("contains '5. Needs Ray approval'",        "5. Needs Ray approval" in formatted)
check("contains '6. What Hermes can do next'",   "6. What Hermes can do next" in formatted)
check("contains 'Approval boundary'",            "Approval boundary" in formatted)
check("approval boundary text present",
      "will not publish" in formatted.lower() or "approval" in formatted.lower())

# ── run_command routing ────────────────────────────────────────────────────
print("\n-- run_command routing for daily_operating_cycle --")
from hermes_command_router.router import run_command
for phrase in [
    "run daily operating cycle",
    "what should i work on today",
    "show today's nexus plan",
    "show today's plan",
    "daily plan",
]:
    resp = run_command(phrase, source="cli")
    check(f"'{phrase}': non-empty", bool(resp))
    check(f"'{phrase}': TODAY'S NEXUS PLAN", "TODAY'S NEXUS PLAN" in resp)

# ── no evidence dump ───────────────────────────────────────────────────────
print("\n-- no evidence dump in plan --")
DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory",
                "I can answer from verified", "═══", "HERMES REPORT"]
check("no evidence dump in formatted",
      not any(m in formatted for m in DUMP_MARKERS))

# ── without arguments (no inputs) ─────────────────────────────────────────
print("\n-- build_daily_operating_plan with no arguments --")
plan2 = build_daily_operating_plan()
check("works without inputs argument", isinstance(plan2, dict))
check("has required keys",
      all(k in plan2 for k in ["date", "top_priority", "top_revenue", "blockers"]))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
