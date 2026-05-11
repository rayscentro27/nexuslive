"""Predefined swarm scenarios (preview-only, read-only)."""
from __future__ import annotations

from copy import deepcopy

from lib.swarm_orchestration_foundation import build_swarm_preview


_SCENARIOS: dict[str, dict] = {
    "funding_onboarding": {
        "scenario_id": "funding_onboarding",
        "display_name": "Funding Onboarding",
        "description": "Initial client onboarding for funding strategy pathing.",
        "initiating_role": "ceo_router",
        "delegated_roles": ["credit_ai", "funding_ai", "crm_copilot"],
        "task_sequence": ["credit_analysis", "funding_strategy", "cheap_summary"],
        "risk_level": "high",
        "approval_required": True,
        "execution_mode": "preview_only",
        "can_execute": False,
    },
    "credit_remediation": {
        "scenario_id": "credit_remediation",
        "display_name": "Credit Remediation",
        "description": "Credit profile remediation planning and follow-up workflow.",
        "initiating_role": "credit_ai",
        "delegated_roles": ["funding_ai", "crm_copilot"],
        "task_sequence": ["credit_analysis", "funding_strategy", "cheap_summary"],
        "risk_level": "high",
        "approval_required": True,
        "execution_mode": "preview_only",
        "can_execute": False,
    },
    "grant_research": {
        "scenario_id": "grant_research",
        "display_name": "Grant Research",
        "description": "Grant opportunity research and readiness follow-up.",
        "initiating_role": "grants_ai",
        "delegated_roles": ["crm_copilot"],
        "task_sequence": ["research_worker", "cheap_summary"],
        "risk_level": "medium",
        "approval_required": True,
        "execution_mode": "preview_only",
        "can_execute": False,
    },
    "ops_incident_triage": {
        "scenario_id": "ops_incident_triage",
        "display_name": "Ops Incident Triage",
        "description": "Operational incident triage and escalation plan.",
        "initiating_role": "ops_monitoring_ai",
        "delegated_roles": ["ceo_router"],
        "task_sequence": ["cheap_summary", "premium_reasoning"],
        "risk_level": "high",
        "approval_required": True,
        "execution_mode": "preview_only",
        "can_execute": False,
    },
    "business_setup_readiness": {
        "scenario_id": "business_setup_readiness",
        "display_name": "Business Setup Readiness",
        "description": "Business setup sequencing tied to readiness and funding outcomes.",
        "initiating_role": "business_setup_ai",
        "delegated_roles": ["credit_ai", "funding_ai"],
        "task_sequence": ["premium_reasoning", "credit_analysis", "funding_strategy"],
        "risk_level": "medium",
        "approval_required": True,
        "execution_mode": "preview_only",
        "can_execute": False,
    },
    "trading_research_review": {
        "scenario_id": "trading_research_review",
        "display_name": "Trading Research Review",
        "description": "Research strategy review with operations guardrails.",
        "initiating_role": "trading_research_ai",
        "delegated_roles": ["ops_monitoring_ai", "ceo_router"],
        "task_sequence": ["research_worker", "cheap_summary", "premium_reasoning"],
        "risk_level": "high",
        "approval_required": True,
        "execution_mode": "preview_only",
        "can_execute": False,
    },
}


def list_swarm_scenarios() -> list[dict]:
    return [deepcopy(v) for v in _SCENARIOS.values()]


def get_swarm_scenario(scenario_id: str) -> dict | None:
    row = _SCENARIOS.get(scenario_id)
    return deepcopy(row) if row else None


def build_scenario_preview(scenario_id: str) -> dict:
    scenario = get_swarm_scenario(scenario_id)
    if not scenario:
        return {
            "error": "scenario_not_found",
            "scenario_id": scenario_id,
            "approval_required": True,
            "execution_mode": "preview_only",
            "can_execute": False,
            "status": "blocked",
            "reason": "Scenario is not defined.",
        }

    swarm = build_swarm_preview(
        initiating_role=scenario["initiating_role"],
        objective=scenario["description"],
        delegated_roles=scenario["delegated_roles"],
    )
    return {
        "scenario": scenario,
        "swarm_preview": swarm,
    }
