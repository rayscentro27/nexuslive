"""
test_daily_cycle_state_no_secrets.py
Tests: sanitize_daily_cycle_state and save_daily_cycle_state never leak secrets,
       tokens, raw client data, or approval_boundary payloads.
"""
import sys, os, json
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


print("=== test_daily_cycle_state_no_secrets ===\n")

from lib.hermes_daily_cycle_state import (
    sanitize_daily_cycle_state, save_daily_cycle_state,
    load_latest_daily_cycle_state, _OP_STATE_FILE,
)

POISON_PLAN = {
    "date": "2026-06-02",
    "top_priority": "Build lead magnet",
    "_errors": ["some internal error detail"],
    "approval_boundary": "SECRET APPROVAL BOUNDARY",
    "loaded_at": "2026-06-02T12:00:00Z",
    "top_revenue": {
        "action": "Advance lead magnet",
        "asset_name": "checklist.pdf",
        "asset_path": "/tmp/checklist.pdf",
        "asset_type": "pdf",
        "next_step": "Review",
        "approval_needed": "Ray approval",
        "why": "Top asset",
        "supabase_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.SECRET",
        "raw_payload": {"client_email": "client@example.com", "ssn": "123-45-6789"},
        "api_token": "sk-live-SECRET_TOKEN",
    },
    "top_asset": {
        "asset_name": "checklist.pdf",
        "asset_type": "pdf",
        "asset_path": "/tmp/checklist.pdf",
        "why": "Top asset",
        "stripe_secret": "sk_live_SECRET",
    },
    "blockers": [
        {"blocker": "CTA missing", "category": "operational", "fix": "Draft CTA",
         "raw_client_data": "PRIVATE_DATA"},
    ],
    "approval_items": [
        {"item": "Approve newsletter", "category": "action_queue",
         "why": "Ready", "next_if_approved": "Send", "risk_if_skipped": "Delayed",
         "supabase_payload": {"key": "SECRET_KEY"}},
    ],
    "memory_v2_count": 5,
    "goals_count": 2,
    "action_count": 3,
}

# ── sanitize strips forbidden fields ─────────────────────────────────────────
print("-- sanitize_daily_cycle_state strips secrets --")
safe = sanitize_daily_cycle_state(POISON_PLAN)
safe_str = json.dumps(safe)

check("approval_boundary not in safe", "approval_boundary" not in safe)
check("_errors not in safe", "_errors" not in safe)
check("loaded_at not in safe", "loaded_at" not in safe)
check("supabase_key not in safe_str", "supabase_key" not in safe_str)
check("api_token not in safe_str", "api_token" not in safe_str)
check("stripe_secret not in safe_str", "stripe_secret" not in safe_str)
check("raw_client_data not in safe_str", "raw_client_data" not in safe_str)
check("supabase_payload not in safe_str", "supabase_payload" not in safe_str)
check("eyJhbGci (JWT token fragment) not in safe_str", "eyJhbGci" not in safe_str)
check("sk-live not in safe_str", "sk-live" not in safe_str)
check("sk_live not in safe_str", "sk_live" not in safe_str)
check("PRIVATE_DATA not in safe_str", "PRIVATE_DATA" not in safe_str)

# ── safe fields are still present ────────────────────────────────────────────
print("\n-- safe fields preserved --")
check("top_priority preserved", safe.get("top_priority") == "Build lead magnet")
check("top_revenue.action preserved", (safe.get("top_revenue") or {}).get("action") == "Advance lead magnet")
check("blockers preserved (1 item)", len(safe.get("blockers") or []) == 1)
check("blocker text preserved", (safe.get("blockers") or [{}])[0].get("blocker") == "CTA missing")

# ── saved state file also clean ───────────────────────────────────────────────
print("\n-- state file on disk is clean --")
save_daily_cycle_state(POISON_PLAN)
disk_str = _OP_STATE_FILE.read_text()
check("supabase_key not in disk file", "supabase_key" not in disk_str)
check("api_token not in disk file", "api_token" not in disk_str)
check("sk_live not in disk file", "sk_live" not in disk_str)
check("eyJhbGci not in disk file", "eyJhbGci" not in disk_str)
check("approval_boundary not in disk file", "approval_boundary" not in disk_str)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
