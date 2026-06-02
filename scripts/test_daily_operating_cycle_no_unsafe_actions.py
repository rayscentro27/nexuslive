"""
test_daily_operating_cycle_no_unsafe_actions.py
Tests: daily cycle never executes unsafe actions (no publish/spend/trade/deploy).
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


print("=== test_daily_operating_cycle_no_unsafe_actions ===\n")

import inspect
from lib.hermes_daily_operating_cycle import (
    build_daily_operating_plan,
    format_daily_operating_plan,
    format_approval_needed_summary,
    format_continue_while_out_plan,
    format_top_revenue_move,
    format_blockers_summary,
    APPROVAL_BOUNDARY,
    BLOCKED_ACTIONS,
)

# ── APPROVAL_BOUNDARY contains required language ──────────────────────────
print("-- APPROVAL_BOUNDARY: required safety language --")
boundary = APPROVAL_BOUNDARY.lower()
check("mentions publish",           "publish" in boundary)
check("mentions email",             "email" in boundary)
check("mentions sell or live trade","sell" in boundary or "live trading" in boundary)
check("mentions deploy",            "deploy" in boundary)
check("mentions spend money",       "spend money" in boundary or "money" in boundary)
check("mentions affiliate",         "affiliate" in boundary)
check("requires Ray approval",      "ray" in boundary or "approval" in boundary)

# ── BLOCKED_ACTIONS lists all dangerous categories ────────────────────────
print("\n-- BLOCKED_ACTIONS: dangerous categories present --")
blocked_lower = " ".join(a.lower() for a in BLOCKED_ACTIONS)
check("publish in blocked",         "publish" in blocked_lower)
check("email in blocked",           "email" in blocked_lower or "subscriber" in blocked_lower)
check("spend money in blocked",     "spend money" in blocked_lower)
check("affiliate in blocked",       "affiliate" in blocked_lower)
check("deploy in blocked",          "deploy" in blocked_lower)
check("live trading in blocked",    "live trading" in blocked_lower or "live trade" in blocked_lower)

# ── Source code never calls publish/deploy/trade ──────────────────────────
print("\n-- source code: no unsafe write calls --")
import lib.hermes_daily_operating_cycle as _mod
src = inspect.getsource(_mod)
FORBIDDEN_CALLS = [
    ".insert(", ".update(", ".delete(",  # Supabase writes (should never happen here)
]
OLD_TABLES = [
    "'ai_memory'", '"ai_memory"',
    "'hermes_executive_memory'", '"hermes_executive_memory"',
    "'knowledge_items'", '"knowledge_items"',
]
for call in FORBIDDEN_CALLS:
    check(f"no Supabase write call {call!r} in module", call not in src)
for tbl in OLD_TABLES:
    check(f"no old table {tbl} in module", tbl not in src)

# ── Plan output never commands unsafe actions ─────────────────────────────
print("\n-- plan output: no unsafe action commands --")
plan = build_daily_operating_plan()
formatted = format_daily_operating_plan(plan)

# These phrases must NOT appear as action commands (not counting the approval boundary disclaimer)
UNSAFE_COMMAND_PHRASES = [
    "publish this",
    "send to subscribers",
    "execute live trade",
    "submit live order",
    "deploy to production",
    "spend money on",
    "activate stripe",
    "charge customers",
]
for phrase in UNSAFE_COMMAND_PHRASES:
    check(f"plan: no '{phrase}'", phrase.lower() not in formatted.lower())
# "apply to affiliate" appears in approval boundary "I will not" — that's acceptable
check("plan: no 'apply now' to affiliate program",
      "apply now" not in formatted.lower() and "affiliate program now" not in formatted.lower())

# ── Approval boundary appears in every output ─────────────────────────────
print("\n-- approval boundary in every formatted output --")
outputs = {
    "daily plan":       format_daily_operating_plan(plan),
    "approval summary": format_approval_needed_summary(plan),
    "top revenue move": format_top_revenue_move(plan),
}
for name, output in outputs.items():
    check(f"{name}: contains 'Approval'",
          "Approval" in output or "approval" in output)

# ── continue_while_out explicitly lists blocked actions ───────────────────
print("\n-- continue_while_out: blocked list is explicit --")
cwo = format_continue_while_out_plan()
check("I will not section present",         "I will not:" in cwo)
check("publish in I will not section",      "publish" in cwo.lower())
check("live trading in I will not section", "live trading" in cwo.lower() or "live trade" in cwo.lower())
check("spend money in I will not section",  "spend money" in cwo.lower())

# ── module source: no old_executive_memory references ────────────────────
print("\n-- no old executive memory references --")
EXEC_MEM_REFS = [
    "hermes_executive_memory",
    "ExecutiveMemory",
    "executive_memory_snapshot",
    ".hermes_executive_memory",
]
for ref in EXEC_MEM_REFS:
    check(f"no '{ref}' in module source", ref not in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
