from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass


AGENT_REGISTRY: dict[str, dict] = {
    "ops_monitor": {
        "name": "Ops Monitor Agent",
        "responsibility": "System health, queue and worker status monitoring.",
        "allowed_job_types": ["system_health_check", "worker_status_check", "queue_status_check", "backend_health_report"],
        "risk_level": "medium",
        "allowed_actions": ["monitor", "summarize"],
        "requires_approval_for": ["deploy", "config_change", "delete"],
        "preferred_model_route": "cheap_summary",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "telegram_comms": {
        "name": "Telegram/Comms Agent",
        "responsibility": "Drafts operator-facing communication plans only.",
        "allowed_job_types": ["telegram_routing_review", "report_writer"],
        "risk_level": "medium",
        "allowed_actions": ["draft", "summarize"],
        "requires_approval_for": ["client_message", "external_send"],
        "preferred_model_route": "cheap_summary",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "funding_strategy": {
        "name": "Funding Strategy Agent",
        "responsibility": "Funding track and lender-fit strategy planning.",
        "allowed_job_types": ["funding_strategy_review"],
        "risk_level": "high",
        "allowed_actions": ["analyze", "recommend"],
        "requires_approval_for": ["client_message", "billing_change"],
        "preferred_model_route": "funding_strategy",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "credit_workflow": {
        "name": "Credit Workflow Agent",
        "responsibility": "Credit readiness workflow diagnostics.",
        "allowed_job_types": ["credit_workflow_review"],
        "risk_level": "high",
        "allowed_actions": ["analyze", "recommend"],
        "requires_approval_for": ["client_message", "external_send"],
        "preferred_model_route": "credit_analysis",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "grants_research": {
        "name": "Grants Research Agent",
        "responsibility": "Grants opportunity triage and review.",
        "allowed_job_types": ["grants_review"],
        "risk_level": "medium",
        "allowed_actions": ["research", "summarize"],
        "requires_approval_for": ["client_message", "external_send"],
        "preferred_model_route": "research_worker",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "business_setup": {
        "name": "Business Setup Agent",
        "responsibility": "Business setup workflow planning.",
        "allowed_job_types": ["business_setup_review"],
        "risk_level": "medium",
        "allowed_actions": ["analyze", "plan"],
        "requires_approval_for": ["deploy", "config_change"],
        "preferred_model_route": "premium_reasoning",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "crm_followup": {
        "name": "CRM Follow-up Agent",
        "responsibility": "Follow-up cadence and CRM next actions.",
        "allowed_job_types": ["crm_followup_review"],
        "risk_level": "medium",
        "allowed_actions": ["analyze", "recommend"],
        "requires_approval_for": ["client_message", "external_send"],
        "preferred_model_route": "cheap_summary",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "trading_research": {
        "name": "Trading Research Agent",
        "responsibility": "Trading research summarization and review.",
        "allowed_job_types": ["trading_research_review"],
        "risk_level": "high",
        "allowed_actions": ["research", "summarize"],
        "requires_approval_for": ["trade_execution", "client_message"],
        "preferred_model_route": "research_worker",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "qa_test": {
        "name": "QA/Test Agent",
        "responsibility": "Validation and regression checks.",
        "allowed_job_types": ["qa_validation"],
        "risk_level": "low",
        "allowed_actions": ["validate", "summarize"],
        "requires_approval_for": ["deploy"],
        "preferred_model_route": "cheap_summary",
        "output_destination": "workflow_outputs",
        "telegram_allowed": False,
    },
    "report_writer": {
        "name": "Report Writer Agent",
        "responsibility": "Produces email-first report drafts.",
        "allowed_job_types": ["report_writer"],
        "risk_level": "low",
        "allowed_actions": ["draft", "summarize"],
        "requires_approval_for": ["client_message"],
        "preferred_model_route": "cheap_summary",
        "output_destination": "email_report",
        "telegram_allowed": False,
    },
}

RISKY_TOKENS = {"deploy", "migration", "bill", "delete", "production", "client message", "external message", "config"}


def list_agents() -> list[dict]:
    rows = []
    for role_id, cfg in AGENT_REGISTRY.items():
        row = deepcopy(cfg)
        row["role_id"] = role_id
        rows.append(row)
    return rows


def _goal_tokens(goal: str) -> set[str]:
    return set((goal or "").lower().replace("_", " ").split())


def _select_role(goal: str) -> str:
    txt = (goal or "").lower()
    if "funding" in txt:
        return "funding_strategy"
    if "credit" in txt:
        return "credit_workflow"
    if "grant" in txt:
        return "grants_research"
    if "crm" in txt or "follow" in txt:
        return "crm_followup"
    if "trading" in txt or "signal" in txt:
        return "trading_research"
    if "queue" in txt or "worker" in txt or "health" in txt:
        return "ops_monitor"
    if "report" in txt or "summary" in txt:
        return "report_writer"
    return "qa_test"


def _is_risky(goal: str) -> bool:
    g = (goal or "").lower()
    return any(tok in g for tok in RISKY_TOKENS)


@dataclass
class SwarmPlan:
    ok: bool
    goal: str
    dry_run: bool
    assigned_role: str
    approval_required: bool
    blocked: bool
    max_attempts: int
    duplicate_error_suppression: bool
    notes: str

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "goal": self.goal,
            "dry_run": self.dry_run,
            "assigned_role": self.assigned_role,
            "approval_required": self.approval_required,
            "blocked": self.blocked,
            "max_attempts": self.max_attempts,
            "duplicate_error_suppression": self.duplicate_error_suppression,
            "notes": self.notes,
            "execution_mode": "dry_run",
            "can_execute": False,
            "telegram_send_allowed": False,
        }


def assign_task_to_agent(goal: str, agent_role: str) -> dict:
    cfg = AGENT_REGISTRY.get(agent_role)
    if not cfg:
        return {
            "ok": False,
            "error": "unknown_agent_role",
            "goal": goal,
            "assigned_role": agent_role,
            "execution_mode": "dry_run",
            "can_execute": False,
        }
    risky = _is_risky(goal)
    return SwarmPlan(
        ok=True,
        goal=goal,
        dry_run=True,
        assigned_role=agent_role,
        approval_required=risky,
        blocked=False,
        max_attempts=2,
        duplicate_error_suppression=True,
        notes="Dry-run assignment only. No external actions executed.",
    ).to_dict()


def plan_swarm_task(goal: str) -> dict:
    role = _select_role(goal)
    plan = assign_task_to_agent(goal, role)
    if not plan.get("ok"):
        return plan
    if _is_risky(goal):
        plan["approval_required"] = True
        plan["notes"] = "Risky action detected. Approval required before any real execution."
    return plan


def dry_run_swarm_plan(goal: str) -> dict:
    plan = plan_swarm_task(goal)
    plan["dry_run"] = True
    plan["can_execute"] = False
    plan["output_destination"] = AGENT_REGISTRY.get(plan.get("assigned_role"), {}).get("output_destination", "workflow_outputs")
    return plan
