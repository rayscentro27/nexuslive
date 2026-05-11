"""AI Employee role registry (read-only foundation)."""
from __future__ import annotations

from copy import deepcopy


_ROLES: dict[str, dict] = {
    "ceo_router": {
        "role_id": "ceo_router",
        "display_name": "CEO Router",
        "description": "Classifies operator intent and routes work to the right specialist lane.",
        "allowed_task_types": ["premium_reasoning", "telegram_reply", "cheap_summary"],
        "preferred_model_class": "premium_reasoning",
        "risk_level": "medium",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": False,
    },
    "credit_ai": {
        "role_id": "credit_ai",
        "display_name": "Credit AI",
        "description": "Analyzes credit readiness blockers and next-best corrective actions.",
        "allowed_task_types": ["credit_analysis", "cheap_summary"],
        "preferred_model_class": "credit_analysis",
        "risk_level": "high",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": False,
    },
    "funding_ai": {
        "role_id": "funding_ai",
        "display_name": "Funding AI",
        "description": "Maps users to funding strategy tracks and lender-fit recommendations.",
        "allowed_task_types": ["funding_strategy", "cheap_summary"],
        "preferred_model_class": "funding_strategy",
        "risk_level": "high",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": False,
    },
    "grants_ai": {
        "role_id": "grants_ai",
        "display_name": "Grants AI",
        "description": "Tracks grants opportunities and evidence completeness.",
        "allowed_task_types": ["research_worker", "cheap_summary"],
        "preferred_model_class": "research_worker",
        "risk_level": "medium",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": False,
    },
    "business_setup_ai": {
        "role_id": "business_setup_ai",
        "display_name": "Business Setup AI",
        "description": "Produces setup/planning guidance for business launch workflows.",
        "allowed_task_types": ["premium_reasoning", "cheap_summary"],
        "preferred_model_class": "premium_reasoning",
        "risk_level": "medium",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": False,
    },
    "trading_research_ai": {
        "role_id": "trading_research_ai",
        "display_name": "Trading Research AI",
        "description": "Handles strategy/research analysis and summarization workflows.",
        "allowed_task_types": ["research_worker", "cheap_summary"],
        "preferred_model_class": "research_worker",
        "risk_level": "high",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": False,
    },
    "crm_copilot": {
        "role_id": "crm_copilot",
        "display_name": "CRM Copilot",
        "description": "Surfaces outreach priorities, churn risk, and engagement suggestions.",
        "allowed_task_types": ["premium_reasoning", "cheap_summary"],
        "preferred_model_class": "premium_reasoning",
        "risk_level": "medium",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": False,
    },
    "ops_monitoring_ai": {
        "role_id": "ops_monitoring_ai",
        "display_name": "Ops Monitoring AI",
        "description": "Monitors worker health, retries, and critical operational anomalies.",
        "allowed_task_types": ["cheap_summary", "telegram_reply"],
        "preferred_model_class": "cheap_summary",
        "risk_level": "high",
        "can_auto_execute": False,
        "requires_admin_approval": True,
        "telegram_allowed": True,
        "telegram_scope": "critical_only",
    },
}


def list_roles() -> list[dict]:
    return [deepcopy(v) for v in _ROLES.values()]


def get_role(role_id: str) -> dict | None:
    role = _ROLES.get(role_id)
    return deepcopy(role) if role else None


def validate_role_task(role_id: str, task_type: str) -> bool:
    role = _ROLES.get(role_id)
    if not role:
        return False
    return task_type in role.get("allowed_task_types", [])


def role_routing_preview(role_id: str) -> dict:
    role = _ROLES.get(role_id)
    if not role:
        return {"role_id": role_id, "error": "role_not_found"}
    task = role.get("preferred_model_class", "cheap_summary")
    try:
        from lib.model_router import routing_preview

        rp = routing_preview(task_type=task)
        return {
            "role_id": role_id,
            "preferred_model_class": task,
            "routing_preview": rp,
        }
    except Exception as e:
        return {
            "role_id": role_id,
            "preferred_model_class": task,
            "routing_preview": None,
            "error": type(e).__name__,
        }
