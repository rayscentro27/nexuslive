"""
test_daily_cycle_state_save_load.py
Tests: save_daily_cycle_state writes state file; load_latest_daily_cycle_state reads it back.
"""
import sys, os, json, tempfile
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


print("=== test_daily_cycle_state_save_load ===\n")

from lib.hermes_daily_cycle_state import (
    save_daily_cycle_state, load_latest_daily_cycle_state,
    sanitize_daily_cycle_state, _OP_STATE_FILE,
)

SAMPLE_PLAN = {
    "date": "2026-06-02",
    "top_priority": "Advance lead magnet",
    "top_priority_why": "Highest-value asset ready",
    "top_revenue": {
        "action": "Advance lead magnet content",
        "asset_name": "funding_checklist.pdf",
        "asset_path": "/tmp/funding_checklist.pdf",
        "asset_type": "pdf",
        "next_step": "Review and prepare for approval",
        "approval_needed": "Ray approval required",
        "why": "Top revenue asset",
    },
    "blockers": [
        {"blocker": "Newsletter not approved", "category": "approval", "fix": "Request Ray approval"},
        {"blocker": "Lead magnet missing CTA", "category": "operational", "fix": "Draft CTA section"},
    ],
    "approval_items": [
        {
            "item": "Publish newsletter draft",
            "category": "action_queue",
            "why": "Ready to send to subscribers",
            "next_if_approved": "Send via email platform",
            "risk_if_skipped": "Revenue delayed",
        },
    ],
    "evidence": ["goal: Build Nexus revenue engine", "artifact: /tmp/funding_checklist.pdf"],
    "safe_next_actions": ["Review source intake", "Score monetization opportunities"],
    "memory_v2_count": 12,
    "goals_count": 3,
    "action_count": 5,
    "approval_boundary": "I will not publish without Ray approval.",
}

# ── save writes state file ────────────────────────────────────────────────────
print("-- save_daily_cycle_state --")
saved = save_daily_cycle_state(SAMPLE_PLAN)
check("returns dict", isinstance(saved, dict))
check("contains 'created_at'", "created_at" in saved)
check("contains top_priority", saved.get("top_priority") == "Advance lead magnet")
check("state file exists on disk", _OP_STATE_FILE.exists())

# ── load reads back state file ────────────────────────────────────────────────
print("\n-- load_latest_daily_cycle_state --")
loaded = load_latest_daily_cycle_state()
check("returns dict (not None)", loaded is not None)
check("top_priority matches", (loaded or {}).get("top_priority") == "Advance lead magnet")
check("date matches", (loaded or {}).get("date") == "2026-06-02")
check("blockers list present", isinstance((loaded or {}).get("blockers"), list))
check("approval_items list present", isinstance((loaded or {}).get("approval_items"), list))
check("completed_items initialized", isinstance((loaded or {}).get("completed_items"), list))

# ── state file is valid JSON ──────────────────────────────────────────────────
print("\n-- state file is valid JSON --")
try:
    raw = json.loads(_OP_STATE_FILE.read_text())
    check("state file parses as JSON", True)
    check("JSON top_priority correct", raw.get("top_priority") == "Advance lead magnet")
except Exception as exc:
    check(f"state file parses as JSON (exception: {exc})", False)
    check("JSON top_priority correct", False)

# ── approval_boundary stripped (not sensitive but excluded from state) ─────────
print("\n-- approval_boundary excluded from state --")
check("approval_boundary not in saved", "approval_boundary" not in saved)
check("approval_boundary not in loaded", "approval_boundary" not in (loaded or {}))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
