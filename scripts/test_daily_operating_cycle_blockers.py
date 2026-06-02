"""
test_daily_operating_cycle_blockers.py
Tests: find_current_blockers and format_blockers_summary — never invents stale issues.
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


print("=== test_daily_operating_cycle_blockers ===\n")

from lib.hermes_daily_operating_cycle import (
    build_daily_operating_plan,
    format_blockers_summary,
    find_current_blockers,
)

# ── find_current_blockers: empty inputs → no blockers ─────────────────────
print("-- find_current_blockers: empty inputs --")
empty_inputs = {
    "action_queue": [], "knowledge_gaps": [], "decisions": [],
}
blockers_empty = find_current_blockers(empty_inputs)
check("empty inputs: blockers is list",  isinstance(blockers_empty, list))
check("empty inputs: no blockers",       len(blockers_empty) == 0)

# ── find_current_blockers: blocked action detected ────────────────────────
print("\n-- find_current_blockers: blocked action --")
inputs_with_blocked = {
    "action_queue": [{
        "action_id": "act_test1",
        "title": "Process YouTube playlist for research",
        "status": "blocked",
        "next_step": "Wait for YouTube API key to be configured.",
        "requires_ray_approval": False,
    }],
    "knowledge_gaps": [],
    "decisions": [],
}
blockers_blocked = find_current_blockers(inputs_with_blocked)
check("blocked action: 1 blocker found",             len(blockers_blocked) >= 1)
check("blocked action: blocker has 'blocker' key",   "blocker" in blockers_blocked[0])
check("blocked action: blocker has 'category' key",  "category" in blockers_blocked[0])
check("blocked action: blocker has 'fix' key",       "fix" in blockers_blocked[0])
check("blocked action: title in blocker text",
      "Process YouTube" in blockers_blocked[0].get("blocker", ""))

# ── find_current_blockers: approval-pending ───────────────────────────────
print("\n-- find_current_blockers: approval-pending action --")
inputs_with_approval = {
    "action_queue": [{
        "action_id": "act_test2",
        "title": "Publish lead magnet to landing page",
        "status": "needs_ray_approval",
        "requires_ray_approval": True,
        "approval_reason": "Requires Ray sign-off before publishing.",
        "next_step": "",
    }],
    "knowledge_gaps": [],
    "decisions": [],
}
blockers_approval = find_current_blockers(inputs_with_approval)
check("approval-pending: at least 1 blocker",        len(blockers_approval) >= 1)
check("approval-pending: category is 'approval'",
      any(b.get("category") == "approval" for b in blockers_approval))

# ── find_current_blockers: knowledge gaps as soft blocker ─────────────────
print("\n-- find_current_blockers: knowledge gaps --")
inputs_with_gaps = {
    "action_queue": [],
    "knowledge_gaps": [
        {"status": "open", "category": "market_data", "user_message": "what is the current trend?"},
        {"status": "open", "category": "provider",    "user_message": "what tools are available?"},
    ],
    "decisions": [],
}
blockers_gaps = find_current_blockers(inputs_with_gaps)
check("knowledge gaps: soft blocker present",        len(blockers_gaps) >= 1)
check("knowledge gaps: category is 'knowledge'",
      any(b.get("category") == "knowledge" for b in blockers_gaps))

# ── format_blockers_summary: structure ───────────────────────────────────
print("\n-- format_blockers_summary: structure --")
plan = build_daily_operating_plan()
resp = format_blockers_summary(plan)

check("non-empty",                               bool(resp))
check("starts with TODAY'S BLOCKERS",            resp.startswith("TODAY'S BLOCKERS"))
check("contains date",                           plan["date"] in resp)
check("contains 'Critical blockers:'",           "Critical blockers:" in resp)
check("contains 'Operational blockers:'",        "Operational blockers:" in resp)

# ── no stale provider claims ──────────────────────────────────────────────
print("\n-- no stale provider claims --")
STALE_MARKERS = ["provider snapshot", "executive memory", "stale memory",
                 "hermes executive", "last checked 2025", "last checked 2024"]
check("no stale provider claims in blockers",
      not any(m in resp.lower() for m in STALE_MARKERS))

# ── no evidence dump ──────────────────────────────────────────────────────
print("\n-- no evidence dump --")
DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory",
                "I can answer from verified", "═══", "HERMES REPORT"]
check("no evidence dump",
      not any(m in resp for m in DUMP_MARKERS))

# ── routing ────────────────────────────────────────────────────────────────
print("\n-- routing: daily_blockers intent --")
from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

for phrase in [
    "show today's blockers",
    "show blockers",
    "what is blocked",
    "what is stopping us",
    "current blockers",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == daily_blockers", intent == "daily_blockers")
    resp_r = run_command(phrase, source="cli")
    check(f"'{phrase}': non-empty",                    bool(resp_r))
    check(f"'{phrase}': TODAY'S BLOCKERS",             "TODAY'S BLOCKERS" in resp_r)
    check(f"'{phrase}': no evidence dump",
          not any(m in resp_r for m in DUMP_MARKERS))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
