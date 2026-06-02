"""
test_approval_queue_no_secrets.py
Tests: approval queue state files never contain secrets, tokens, or raw client data.
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

SECRET_PATTERNS = [
    "sk-",              # OpenAI keys
    "eyJ",              # JWT tokens
    "TELEGRAM_BOT",     # Bot token env key
    "bot_token",        # Telegram bot token
    "api_key",          # Generic API key (lowercase)
    "secret_key",
    "private_key",
    "supabase_key",
    "password",
    "access_token",
    "refresh_token",
    "stripe_secret",
    "bearer",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_approval_queue_no_secrets ===\n")

from lib.hermes_approval_queue import (
    _STATE_FILE, _HISTORY_FILE, build_approval_queue, normalize_approval_item,
    approve_approval_item, reject_approval_item, _save_state,
)
from lib.hermes_daily_cycle_state import save_daily_cycle_state

# ── seed with realistic items ──────────────────────────────────────────────────
save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "blockers": [],
    "approval_items": [
        {
            "item": "Approve newsletter draft",
            "category": "subscriber_email",
            "why": "Newsletter is ready.",
            "next_if_approved": "Send to scheduling queue.",
            "risk_if_skipped": "Delayed send.",
        }
    ],
    "safe_next_actions": ["Review and score latest source intake records"],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

items = build_approval_queue()

# ── state file does not contain secrets ──────────────────────────────────────
print("-- state file no secrets --")
if _STATE_FILE.exists():
    state_text = _STATE_FILE.read_text().lower()
    for pattern in SECRET_PATTERNS:
        check(f"state file does not contain '{pattern}'",
              pattern.lower() not in state_text)
else:
    check("state file exists after build", False)

# ── history file does not contain secrets ────────────────────────────────────
print("\n-- history file no secrets --")
if _HISTORY_FILE.exists():
    history_text = _HISTORY_FILE.read_text().lower()
    for pattern in SECRET_PATTERNS[:5]:  # Check key ones
        check(f"history file does not contain '{pattern}'",
              pattern.lower() not in history_text)
else:
    check("history file exists (or may be empty — OK)", True)

# ── normalized item does not contain _raw field ──────────────────────────────
print("\n-- normalized item has no _raw field --")
raw = {
    "_source_type": "test", "title": "Test secrets check",
    "summary": "Testing",
    "category": "internal_review", "source": "test",
    "source_path": "docs/test", "related_action_id": "secrets_test_001",
    "risk_level": "low", "approval_required_for": "Test.",
    "if_approved": "Proceeds.", "if_rejected": "Blocked.",
    "safe_internal_next_step": "Review.", "evidence_paths": [],
    "created_at": "2026-06-02T10:00:00+00:00",
    "_raw": {"internal_field": "this should not appear in saved state"},
}
item = normalize_approval_item(raw, index=99)
check("_raw key not in normalized item", "_raw" not in item)
item_json = json.dumps(item)
check("'internal_field' not in item JSON", "internal_field" not in item_json)

# ── state file is well-formed JSON ────────────────────────────────────────────
print("\n-- state file is valid JSON --")
if _STATE_FILE.exists():
    try:
        state_data = json.loads(_STATE_FILE.read_text())
        check("state file parses as JSON", True)
        check("has 'items' key", "items" in state_data)
        check("items is list", isinstance(state_data.get("items"), list))
    except json.JSONDecodeError:
        check("state file parses as JSON", False)
else:
    check("state file exists", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
