"""Safe swarm orchestration foundation (preview-only, no execution)."""
from __future__ import annotations

from typing import Iterable

from lib.ai_employee_registry import get_role


HANDOFF_RULES: dict[str, dict[str, str]] = {
    "ceo_router": {
        "credit_ai": "Credit profile analysis required before funding strategy.",
        "funding_ai": "Funding pathing delegated after intake routing.",
        "grants_ai": "Grant lane needed when non-debt options are requested.",
        "business_setup_ai": "Business setup sequencing needed for readiness.",
        "trading_research_ai": "Research lane needed for strategy questions.",
        "crm_copilot": "Client engagement follow-up required.",
        "ops_monitoring_ai": "Operational visibility required for safe routing.",
    },
    "credit_ai": {
        "funding_ai": "Funding strategy depends on credit readiness output.",
        "crm_copilot": "Client action plan follow-up required.",
    },
    "funding_ai": {
        "credit_ai": "Credit remediation may be required before execution.",
        "crm_copilot": "Client communication and checklist follow-up required.",
    },
    "grants_ai": {
        "crm_copilot": "Grant documentation follow-up required.",
    },
    "business_setup_ai": {
        "credit_ai": "Business setup may impact credit readiness inputs.",
        "funding_ai": "Entity setup may unlock funding stage progression.",
    },
    "trading_research_ai": {
        "ops_monitoring_ai": "Operational guardrails required before strategy rollout.",
    },
    "crm_copilot": {
        "ceo_router": "Escalate to orchestrator for prioritization decisions.",
    },
    "ops_monitoring_ai": {
        "ceo_router": "Escalate anomalies to orchestrator for approval decisions.",
    },
}


def list_handoff_rules() -> dict[str, dict[str, str]]:
    return {k: dict(v) for k, v in HANDOFF_RULES.items()}


def get_allowed_delegates(role_id: str) -> list[str]:
    return sorted(list(HANDOFF_RULES.get(role_id, {}).keys()))


def _decision(initiating_role: str, delegated_role: str) -> tuple[bool, str]:
    reason = HANDOFF_RULES.get(initiating_role, {}).get(delegated_role)
    if reason:
        return True, reason
    return False, f"No safe handoff rule from {initiating_role} to {delegated_role}."


def build_swarm_preview(
    initiating_role: str,
    objective: str,
    delegated_roles: Iterable[str] | None = None,
) -> dict:
    initiator = get_role(initiating_role)
    if not initiator:
        return {
            "error": "invalid_initiating_role",
            "initiating_role": initiating_role,
            "objective": objective,
            "approval_required": True,
            "status": "blocked",
            "reason": "Initiating role not found in registry.",
        }

    requested = list(delegated_roles or get_allowed_delegates(initiating_role))
    steps: list[dict] = []
    blocked_any = False

    for idx, role_id in enumerate(requested, start=1):
        role = get_role(role_id)
        if not role:
            blocked_any = True
            steps.append(
                {
                    "step": idx,
                    "role_id": role_id,
                    "task_type": "unknown",
                    "model_class": "unknown",
                    "approval_required": True,
                    "risk_level": "high",
                    "status": "blocked",
                    "allowed": False,
                    "reason": "Delegated role not found in registry.",
                }
            )
            continue

        allowed, reason = _decision(initiating_role, role_id)
        if not allowed:
            blocked_any = True
        task = (role.get("allowed_task_types") or ["cheap_summary"])[0]
        steps.append(
            {
                "step": idx,
                "role_id": role_id,
                "display_name": role.get("display_name"),
                "task_type": task,
                "model_class": role.get("preferred_model_class"),
                "approval_required": True,
                "risk_level": role.get("risk_level", "medium"),
                "status": "blocked" if not allowed else "awaiting_admin_approval",
                "allowed": allowed,
                "reason": reason,
            }
        )

    return {
        "initiating_role": initiating_role,
        "objective": objective,
        "delegated_roles": requested,
        "task_sequence": steps,
        "approval_required": True,
        "execution_mode": "preview_only",
        "status": "blocked" if blocked_any else "awaiting_admin_approval",
        "can_execute": False,
        "reason": "Autonomous swarm execution is disabled by policy.",
    }
