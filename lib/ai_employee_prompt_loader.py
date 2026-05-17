from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = ROOT / "ai_employees" / "prompts"
PROFILES_PATH = ROOT / "ai_employees" / "employee_profiles.json"

PROMPT_FILE_MAP = {
    "hermes": "hermes_ops_prompt.md",
    "trading_analyst": "sage_trading_prompt.md",
    "credit_coach": "vera_credit_prompt.md",
    "funding_strategist": "rex_funding_prompt.md",
    "grant_researcher": "aria_grants_prompt.md",
    "business_opportunity": "nova_business_opportunities_prompt.md",
    "marketing_researcher": "mira_marketing_prompt.md",
    "system_monitor": "orion_system_monitor_prompt.md",
}


def _read_profiles() -> dict[str, Any]:
    try:
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_employee_prompt(employee_id: str) -> str:
    filename = PROMPT_FILE_MAP.get(employee_id, "")
    if not filename:
        return ""
    path = PROMPT_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def get_employee_voice(employee_id: str) -> str:
    profiles = _read_profiles()
    return str((profiles.get(employee_id) or {}).get("voice") or "professional")


def get_employee_decision_framework(employee_id: str) -> str:
    profiles = _read_profiles()
    return str((profiles.get(employee_id) or {}).get("decision_framework") or "supabase_first_then_escalate")


def get_employee_confidence_threshold(employee_id: str, default: int = 50) -> int:
    profiles = _read_profiles()
    raw = (profiles.get(employee_id) or {}).get("confidence_threshold", default)
    try:
        return int(raw)
    except Exception:
        return default
