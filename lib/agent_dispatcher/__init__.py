"""
Nexus Agent Dispatcher — foundation package.

Coordinates task planning, agent selection, risk assessment,
and subtask routing. Extends the existing ai_task_dispatch system
with structured planning, agent/skill/CLI registries, and approval gates.
"""
from .registry import (
    load_agent_capabilities,
    load_nexus_skills,
    load_cli_tools,
    load_available_resources,
)
from .risk import assess_risk, RiskLevel
from .planner import build_task_plan, classify_task_type, decide_clarification_needed
from .router import select_agent, select_provider, route_subtask

__all__ = [
    "load_agent_capabilities",
    "load_nexus_skills",
    "load_cli_tools",
    "load_available_resources",
    "assess_risk",
    "RiskLevel",
    "build_task_plan",
    "classify_task_type",
    "decide_clarification_needed",
    "select_agent",
    "select_provider",
    "route_subtask",
]
