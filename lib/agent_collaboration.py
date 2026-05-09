from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def assign_collaboration_steps(goal: str) -> list[dict[str, Any]]:
    text = (goal or "").lower()
    if "funding" in text:
        return [
            {"agent": "funding_strategy", "mode": "review-only", "action": "review_funding_context"},
            {"agent": "report_writer", "mode": "report-only", "action": "draft_email_report"},
            {"agent": "ops_monitor", "mode": "read-only", "action": "summarize_recommendation"},
        ]
    if "credit" in text:
        return [
            {"agent": "credit_workflow", "mode": "review-only", "action": "review_credit_context"},
            {"agent": "report_writer", "mode": "report-only", "action": "draft_email_report"},
            {"agent": "ops_monitor", "mode": "read-only", "action": "summarize_recommendation"},
        ]
    return [
        {"agent": "ops_monitor", "mode": "read-only", "action": "collect_system_signals"},
        {"agent": "qa_test", "mode": "safe-test-only", "action": "run_safe_checks"},
        {"agent": "report_writer", "mode": "report-only", "action": "draft_email_report"},
    ]


def _supported_goal_type(goal: str) -> str:
    text = (goal or "").lower()
    if any(tok in text for tok in {"funding", "lender", "readiness"}):
        return "funding"
    if any(tok in text for tok in {"credit", "score", "bureau"}):
        return "credit"
    if any(tok in text for tok in {"ops", "worker", "queue", "health", "qa"}):
        return "operations"
    return "unsupported"


def validate_collaboration_safety(plan: dict[str, Any]) -> dict[str, Any]:
    risky_tokens = {"deploy", "migrate", "bill", "delete", "production", "client message", "auto-trade"}
    goal = str(plan.get("goal") or "").lower()
    risky = any(tok in goal for tok in risky_tokens)
    violations = []
    for step in plan.get("steps") or []:
        if step.get("agent") == "telegram_comms":
            violations.append("telegram_comms_not_allowed_in_auto_chain")
    goal_type = _supported_goal_type(goal)
    if goal_type == "unsupported":
        violations.append("unsupported_goal_type")
    return {
        "safe": (not risky) and (not violations),
        "approval_required": bool(risky or violations),
        "violations": violations,
        "risky": risky,
        "goal_type": goal_type,
    }


def plan_agent_collaboration(goal: str) -> dict[str, Any]:
    plan = {
        "goal": goal,
        "timestamp": _now(),
        "enabled": _flag("CONTROLLED_AGENT_COLLABORATION_ENABLED", "true"),
        "steps": assign_collaboration_steps(goal),
        "dry_run_only": True,
        "can_execute": False,
        "swarm_execution_enabled": False,
        "output_destination": "email_report",
    }
    plan["safety"] = validate_collaboration_safety(plan)
    if "unsupported_goal_type" in (plan.get("safety") or {}).get("violations", []):
        plan["steps"] = []
        plan["output_destination"] = "operator_review"
    return plan


def dry_run_collaboration_plan(goal: str) -> dict[str, Any]:
    plan = plan_agent_collaboration(goal)
    plan["execution_mode"] = "dry_run"
    return plan


def summarize_collaboration_plan(plan: dict[str, Any]) -> str:
    steps = plan.get("steps") or []
    labels = [f"{s.get('agent')}({s.get('mode')})" for s in steps]
    if plan.get("safety", {}).get("approval_required"):
        return "Collaboration plan drafted in dry-run mode. Approval required before any risky action."
    return "Collaboration plan drafted in dry-run mode: " + " -> ".join(labels)
