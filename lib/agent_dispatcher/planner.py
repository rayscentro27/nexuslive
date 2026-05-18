"""
Nexus Agent Dispatcher — Task Planner.

Takes a natural language prompt, classifies it, and builds a subtask plan
with agent/skill/CLI assignments. Uses the existing resource registry.
"""
from __future__ import annotations

import logging
from typing import Any

from .registry import load_available_resources
from .risk import assess_risk

logger = logging.getLogger("NexusPlanner")

# Task type classifiers: keyword → task_type
_TASK_TYPE_MAP = [
    (["deploy", "launch", "go live", "staging", "production push"], "deploy"),
    (["test", "qa", "review code", "check build"], "qa_review"),
    (["write code", "implement", "add feature", "fix bug", "refactor"], "coding"),
    (["research", "find", "analyze", "what is", "explain"], "research"),
    (["email", "message", "outreach", "follow up", "send"], "comms"),
    (["grant", "sbir", "sba", "funding readiness"], "grants"),
    (["credit", "dispute", "tradeline", "fico"], "credit"),
    (["trading", "strategy", "backtest", "paper trade"], "trading"),
    (["report", "digest", "summary", "ceo brief"], "reporting"),
    (["health", "status", "worker", "provider", "monitor"], "monitoring"),
    (["seo", "keyword", "content", "blog"], "marketing"),
    (["opportunity", "revenue", "monetize", "affiliate"], "opportunities"),
]

# Clarification triggers: vague/risky prompts that need more info
_CLARIFICATION_TRIGGERS = [
    "do everything", "handle all of", "fix everything", "deploy now",
    "go ahead", "just do it", "run it", "launch it",
    "send the message", "approve it", "push it",
]


def classify_task_type(prompt: str) -> str:
    """Classify prompt into a task_type string."""
    text = (prompt or "").lower()
    for keywords, task_type in _TASK_TYPE_MAP:
        if any(kw in text for kw in keywords):
            return task_type
    return "general"


def decide_clarification_needed(prompt: str, resources: dict[str, Any]) -> str | None:
    """
    Returns a clarification question if the prompt is too vague or risky,
    else returns None (proceed with planning).
    """
    text = (prompt or "").lower().strip()
    if not text or len(text) < 8:
        return "What would you like Nexus to do? Please describe the goal."
    for trigger in _CLARIFICATION_TRIGGERS:
        if trigger in text:
            return (
                f"'{trigger}' is too broad for safe execution. "
                "What specific outcome do you need? I'll plan safe subtasks."
            )
    risk = assess_risk(prompt)
    if risk["hard_blocked"]:
        return f"This request is blocked: {risk['block_reason']}. Please clarify the intent."
    return None


def build_task_plan(
    prompt: str,
    task_type: str = "",
    resources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a structured task plan with subtasks and agent assignments.

    Returns:
        {
            "normalized_goal": str,
            "task_type": str,
            "risk": dict,
            "subtasks": list[dict],
            "requires_clarification": str | None,
        }
    """
    if resources is None:
        resources = load_available_resources()

    resolved_task_type = task_type or classify_task_type(prompt)
    risk = assess_risk(prompt, resolved_task_type)
    clarification = decide_clarification_needed(prompt, resources)

    if risk["hard_blocked"] or clarification:
        return {
            "normalized_goal": prompt[:200],
            "task_type": resolved_task_type,
            "risk": risk,
            "subtasks": [],
            "requires_clarification": clarification or f"Blocked: {risk.get('block_reason')}",
        }

    subtasks = _plan_subtasks(prompt, resolved_task_type, risk, resources)

    return {
        "normalized_goal": _normalize_goal(prompt),
        "task_type": resolved_task_type,
        "risk": risk,
        "subtasks": subtasks,
        "requires_clarification": None,
    }


def _normalize_goal(prompt: str) -> str:
    """Remove filler words and normalize the goal statement."""
    text = prompt.strip()
    prefixes = ["can you ", "please ", "i need you to ", "help me ", "i want you to "]
    lower = text.lower()
    for p in prefixes:
        if lower.startswith(p):
            text = text[len(p):]
            break
    return text[:200]


def _plan_subtasks(
    prompt: str,
    task_type: str,
    risk: dict[str, Any],
    resources: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Generate a list of subtasks based on task_type.
    Each subtask includes agent/skill/CLI assignment and approval requirements.
    """
    agents = {a["agent_key"]: a for a in resources.get("agents") or []}
    skills = {s["skill_key"]: s for s in resources.get("skills") or []}
    cli_tools = {c["cli_key"]: c for c in resources.get("cli_tools") or []}
    risk_level = risk.get("risk_level", "low")

    subtasks: list[dict[str, Any]] = []

    def mk_subtask(
        title: str,
        description: str,
        agent_key: str | None = None,
        skill_key: str | None = None,
        cli_key: str | None = None,
        requires_approval: bool = False,
    ) -> dict[str, Any]:
        agent = agents.get(agent_key or "")
        skill = skills.get(skill_key or "")
        cli = cli_tools.get(cli_key or "")
        approval = requires_approval or (
            (agent and agent.get("requires_approval")) or
            (skill and skill.get("requires_approval")) or
            risk_level in {"high", "critical"}
        )
        return {
            "title": title,
            "description": description,
            "task_type": task_type,
            "assigned_agent_key": agent_key,
            "assigned_skill_key": skill_key,
            "assigned_cli_key": cli_key,
            "requires_approval": bool(approval),
            "status": "queued",
        }

    # Route based on task_type
    if task_type == "monitoring":
        subtasks.append(mk_subtask(
            "Run Nexus health check", "nexus health --json",
            cli_key="nexus_health",
        ))
        subtasks.append(mk_subtask(
            "Hermes operational review", "Hermes summarizes operational state",
            agent_key="hermes_orchestrator",
        ))

    elif task_type == "reporting":
        subtasks.append(mk_subtask(
            "Generate CEO digest", "Build operational summary",
            agent_key="hermes_orchestrator", skill_key="ceo_digest_v1",
        ))

    elif task_type == "research":
        subtasks.append(mk_subtask(
            "Research query", f"Research: {_normalize_goal(prompt)}",
            agent_key="research_worker", skill_key="worker_health_audit_v1",
        ))

    elif task_type == "coding":
        subtasks.append(mk_subtask(
            "Analyze codebase context", "Claude Code reads and analyzes relevant files",
            agent_key="claude_code", requires_approval=True,
        ))
        subtasks.append(mk_subtask(
            "Implement changes (dry-run first)", "Apply changes with approval",
            agent_key="claude_code", requires_approval=True,
        ))
        subtasks.append(mk_subtask(
            "QA review", "Validate changes",
            agent_key="qa_worker", skill_key="qa_review_v1",
        ))

    elif task_type == "grants":
        subtasks.append(mk_subtask(
            "Grant scan", "Scan grant catalog for eligible opportunities",
            cli_key="nexus_grants", skill_key="grant_research_v1",
        ))

    elif task_type in {"funding", "credit"}:
        skill_map = {"funding": "funding_readiness_v1", "credit": "credit_dispute_generator_v1"}
        subtasks.append(mk_subtask(
            f"{'Funding readiness' if task_type == 'funding' else 'Credit analysis'}",
            f"Run {task_type} analysis",
            agent_key="hermes_orchestrator",
            skill_key=skill_map[task_type],
        ))

    elif task_type == "comms":
        subtasks.append(mk_subtask(
            "Draft communication", "Draft message — DO NOT auto-send",
            agent_key="nexus_comms_engine", skill_key="client_followup_draft_v1",
            requires_approval=True,
        ))

    else:
        subtasks.append(mk_subtask(
            f"Hermes: {_normalize_goal(prompt)[:60]}",
            f"Hermes handles: {prompt[:200]}",
            agent_key="hermes_orchestrator",
        ))

    return subtasks
