"""
Nexus Agent Dispatcher — Router.

Selects the best agent, provider, and CLI for a given task/subtask.
Applies cost-tiering, health checks, and fallback routing.

Routing priorities:
  1. CLI-first for operational/monitoring tasks (fastest, cheapest)
  2. Existing Hermes/Supabase flows before external tools
  3. Cheap/free models for low-risk repetitive tasks
  4. Claude/Codex for architecture, critical code, complex debugging
  5. Comms Engine only for drafts — never auto-send
  6. Route to fallback if provider is degraded/rate-limited
"""
from __future__ import annotations

import logging
from typing import Any

from .registry import load_agent_capabilities, load_provider_health

logger = logging.getLogger("NexusRouter")

# Provider cost tiers (lower = cheaper/preferred for low-risk tasks)
_PROVIDER_COST_TIER = {
    "ollama": 0,          # free local
    "groq": 1,            # free tier
    "openrouter": 2,      # cheap per-token
    "deepseek": 2,
    "claude_subscription": 3,
    "anthropic": 4,
    "openai": 4,
    "grok_auth": 2,
}

# Agent → preferred provider
_AGENT_PROVIDER_PREFERENCE = {
    "hermes_orchestrator": ["openrouter", "groq", "ollama"],
    "claude_code": ["anthropic", "claude_subscription"],
    "codex_cli": ["openai"],
    "deepseek_tui": ["deepseek"],
    "research_worker": ["openrouter", "groq"],
    "ops_monitor_worker": ["groq", "ollama"],
    "pyrunner_worker": [],  # no LLM needed
}


def _healthy_providers(providers: list[dict[str, Any]]) -> set[str]:
    return {
        str(p.get("provider_name") or p.get("provider_key") or "")
        for p in providers
        if str(p.get("status") or "").lower() in {"online", "healthy"}
    }


def select_agent(
    task_type: str,
    risk_level: str = "low",
    available_agents: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    Select the best available agent for a task_type and risk_level.

    Returns the agent dict or None if no suitable agent found.
    """
    agents = available_agents or load_agent_capabilities()
    candidates = [
        a for a in agents
        if a.get("is_enabled")
        and task_type in (a.get("supported_task_types") or [])
        and risk_level in (a.get("allowed_risk_levels") or ["low"])
    ]
    if not candidates:
        # Fallback: hermes_orchestrator handles most tasks
        for a in agents:
            if a.get("agent_key") == "hermes_orchestrator" and a.get("is_enabled"):
                return a
        return None
    candidates.sort(key=lambda a: int(a.get("priority") or 100))
    return candidates[0]


def select_provider(
    agent_key: str,
    risk_level: str = "low",
    task_type: str = "general",
) -> dict[str, Any]:
    """
    Select the best provider for an agent, given current health.

    Returns:
        {
            "primary": str | None,
            "fallbacks": list[str],
            "reason": str,
        }
    """
    providers = load_provider_health()
    healthy = _healthy_providers(providers)
    preferred = _AGENT_PROVIDER_PREFERENCE.get(agent_key, ["openrouter", "groq"])

    # For low-risk tasks, prefer cheaper providers
    if risk_level == "low" and task_type not in {"coding", "architecture"}:
        cheap_healthy = [p for p in preferred if p in healthy
                        and _PROVIDER_COST_TIER.get(p, 99) <= 2]
        if cheap_healthy:
            return {"primary": cheap_healthy[0], "fallbacks": cheap_healthy[1:], "reason": "cheap_healthy_preferred"}

    # Standard preference order filtered by healthy
    healthy_preferred = [p for p in preferred if p in healthy]
    if healthy_preferred:
        return {"primary": healthy_preferred[0], "fallbacks": healthy_preferred[1:], "reason": "preferred_healthy"}

    # Any healthy provider as fallback
    any_healthy = [p for p in healthy if p]
    if any_healthy:
        return {"primary": any_healthy[0], "fallbacks": any_healthy[1:], "reason": "fallback_healthy"}

    return {"primary": None, "fallbacks": [], "reason": "no_healthy_providers"}


def route_subtask(subtask: dict[str, Any]) -> dict[str, Any]:
    """
    Enrich a subtask dict with routing decisions.

    Adds:
        - assigned_provider_key
        - routing_reason
        - approval_required (confirmed)
    """
    task_type = str(subtask.get("task_type") or "general")
    agent_key = str(subtask.get("assigned_agent_key") or "hermes_orchestrator")
    cli_key = subtask.get("assigned_cli_key")

    # CLI tasks don't need a provider
    if cli_key:
        return {**subtask, "assigned_provider_key": None, "routing_reason": f"cli:{cli_key}"}

    # No LLM needed for Python runner
    if agent_key == "pyrunner_worker":
        return {**subtask, "assigned_provider_key": None, "routing_reason": "pyrunner_no_llm"}

    provider = select_provider(agent_key, subtask.get("risk_level", "low"), task_type)
    return {
        **subtask,
        "assigned_provider_key": provider["primary"],
        "routing_reason": provider["reason"],
        "provider_fallbacks": provider["fallbacks"],
    }
