"""
test_daily_cycle_compare_since_last.py
Tests: compare_since_last_plan intent routes correctly and returns WHAT CHANGED header.
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

DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory", "═══", "HERMES REPORT"]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_daily_cycle_compare_since_last ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS
from lib.hermes_daily_cycle_state import (
    save_daily_cycle_state, compare_current_to_last_cycle
)

save_daily_cycle_state({
    "date": "2026-06-01",
    "top_priority": "Old priority: review source intake",
    "blockers": [{"blocker": "CTA missing", "category": "operational", "fix": "Draft CTA"}],
    "approval_items": [],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

# ── compare_current_to_last_cycle logic ───────────────────────────────────────
print("-- compare_current_to_last_cycle --")
current = {
    "date": "2026-06-02",
    "top_priority": "New priority: advance lead magnet",
    "blockers": [{"blocker": "CTA missing", "category": "operational", "fix": "Draft CTA"},
                 {"blocker": "New blocker added", "category": "approval", "fix": "Get approval"}],
    "approval_items": [{"item": "Approve newsletter", "category": "action_queue",
                        "why": "Ready", "next_if_approved": "Send", "risk_if_skipped": "Delayed"}],
    "evidence": ["goal: Build Nexus"],
    "memory_v2_count": 8, "goals_count": 2, "action_count": 5,
}
prev = {
    "date": "2026-06-01",
    "top_priority": "Old priority: review source intake",
    "blockers": [{"blocker": "CTA missing", "category": "operational", "fix": "Draft CTA"}],
    "approval_items": [],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
}
diff = compare_current_to_last_cycle(current, prev)
check("returns dict", isinstance(diff, dict))
check("priority_changed == True", diff.get("priority_changed") == True)
check("blocker_delta == 1", diff.get("blocker_delta") == 1)
check("approval_delta == 1", diff.get("approval_delta") == 1)
check("changes is a list", isinstance(diff.get("changes"), list))
check("changes non-empty", len(diff.get("changes", [])) > 0)
check("prev_date present", bool(diff.get("prev_date")))
check("curr_date present", bool(diff.get("curr_date")))

# ── no-change diff ────────────────────────────────────────────────────────────
print("\n-- compare_current_to_last_cycle no changes --")
diff_same = compare_current_to_last_cycle(prev, prev)
check("priority_changed == False when same", diff_same.get("priority_changed") == False)
check("no-change message present", "No significant changes" in str(diff_same.get("changes", [])))

# ── intent in _PLAIN_INTENTS ──────────────────────────────────────────────────
print("\n-- compare_since_last_plan in _PLAIN_INTENTS --")
check("compare_since_last_plan in _PLAIN_INTENTS", "compare_since_last_plan" in _PLAIN_INTENTS)

# ── phrase classification ─────────────────────────────────────────────────────
print("\n-- phrase classification --")
PHRASES = [
    "compare since last plan",
    "what changed since last plan",
    "what is new since the last plan",
    "compare to last plan",
    "what changed since yesterday",
    "how has the plan changed",
]
for phrase in PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:50])}) == compare_since_last_plan",
          intent == "compare_since_last_plan")

# ── response structure ────────────────────────────────────────────────────────
print("\n-- run_command response structure --")
resp = run_command("compare since last plan", source="cli")
check("non-empty", bool(resp))
check("starts with WHAT CHANGED SINCE THE LAST PLAN",
      resp.startswith("WHAT CHANGED SINCE THE LAST PLAN"))
check("no dump markers", no_dump(resp))
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no ═══", "═══" not in resp)
check("contains approval boundary", "approval" in resp.lower())
check("no old executive memory", "old executive memory" not in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
