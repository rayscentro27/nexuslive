"""
Nexus Agent Dispatcher — Registry loader.

Loads agent_capabilities, nexus_skills, nexus_cli_tools from Supabase
with in-memory caching. Falls back to embedded minimal registry on failure.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("NexusRegistry")

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_TTL = 120  # 2-minute cache


# ── Embedded fallback registries ──────────────────────────────────────────────

_FALLBACK_AGENTS: list[dict[str, Any]] = [
    {"agent_key": "hermes_orchestrator", "display_name": "Hermes", "agent_type": "hermes",
     "supported_task_types": ["coordination", "analysis", "routing"], "allowed_risk_levels": ["low", "medium", "high"],
     "requires_approval": False, "is_enabled": True, "priority": 1},
    {"agent_key": "claude_code", "display_name": "Claude Code", "agent_type": "claude_code",
     "supported_task_types": ["coding", "refactor", "debugging", "architecture"],
     "allowed_risk_levels": ["low", "medium"], "requires_approval": True, "is_enabled": True, "priority": 10},
    {"agent_key": "pyrunner_worker", "display_name": "Python Runner", "agent_type": "pyrunner",
     "supported_task_types": ["data_processing", "reporting", "ingestion"],
     "allowed_risk_levels": ["low", "medium"], "requires_approval": True, "is_enabled": True, "priority": 40},
    {"agent_key": "research_worker", "display_name": "Research Worker", "agent_type": "research_worker",
     "supported_task_types": ["research", "analysis", "summarization"],
     "allowed_risk_levels": ["low", "medium"], "requires_approval": True, "is_enabled": True, "priority": 80},
]

_FALLBACK_SKILLS: list[dict[str, Any]] = [
    {"skill_key": "funding_readiness_v1", "display_name": "Funding Readiness", "category": "funding",
     "allowed_actions": ["analyze", "recommend"], "risk_level": "low", "requires_approval": False, "is_enabled": True},
    {"skill_key": "grant_research_v1", "display_name": "Grant Research", "category": "grants",
     "allowed_actions": ["research", "analyze", "recommend"], "risk_level": "low", "requires_approval": False, "is_enabled": True},
    {"skill_key": "ceo_digest_v1", "display_name": "CEO Digest", "category": "ops",
     "allowed_actions": ["analyze", "summarize"], "risk_level": "low", "requires_approval": False, "is_enabled": True},
    {"skill_key": "worker_health_audit_v1", "display_name": "Worker Health Audit", "category": "ops",
     "allowed_actions": ["monitor", "analyze"], "risk_level": "low", "requires_approval": False, "is_enabled": True},
]

_FALLBACK_CLI: list[dict[str, Any]] = [
    {"cli_key": "nexus_health", "command_name": "nexus health", "risk_level": "low", "requires_approval": False, "is_enabled": True},
    {"cli_key": "nexus_report", "command_name": "nexus report", "risk_level": "low", "requires_approval": False, "is_enabled": True},
    {"cli_key": "nexus_worker", "command_name": "nexus worker", "risk_level": "low", "requires_approval": True, "is_enabled": True},
    {"cli_key": "nexus_grants", "command_name": "nexus grants", "risk_level": "low", "requires_approval": False, "is_enabled": True},
]


def _rest_select(path: str) -> list[dict[str, Any]] | None:
    try:
        from scripts.prelaunch_utils import rest_select
        rows = rest_select(path, timeout=8) or []
        return [r for r in rows if isinstance(r, dict)] or None
    except Exception as exc:
        logger.debug("registry: rest_select failed: %s", exc)
        return None


def _get_cached(key: str, loader_path: str, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now < cached[0]:
        return cached[1]
    fresh = _rest_select(loader_path)
    rows = fresh if fresh else fallback
    _CACHE[key] = (now + _TTL, rows)
    return rows


def load_agent_capabilities() -> list[dict[str, Any]]:
    """Load enabled agent capabilities, preferring Supabase over fallback."""
    return _get_cached(
        "agents",
        "agent_capabilities?is_enabled=eq.true&order=priority.asc",
        _FALLBACK_AGENTS,
    )


def load_nexus_skills() -> list[dict[str, Any]]:
    """Load enabled Nexus skills."""
    return _get_cached(
        "skills",
        "nexus_skills?is_enabled=eq.true&order=category.asc",
        _FALLBACK_SKILLS,
    )


def load_cli_tools() -> list[dict[str, Any]]:
    """Load enabled CLI tools."""
    return _get_cached(
        "cli_tools",
        "nexus_cli_tools?is_enabled=eq.true",
        _FALLBACK_CLI,
    )


def load_provider_health() -> list[dict[str, Any]]:
    """Load current provider health from existing provider_health table."""
    rows = _rest_select("provider_health?order=provider_name.asc")
    return rows if rows else []


def load_available_resources() -> dict[str, Any]:
    """Return a consolidated snapshot of all available workforce resources."""
    agents = load_agent_capabilities()
    skills = load_nexus_skills()
    cli_tools = load_cli_tools()
    providers = load_provider_health()

    online_providers = [p for p in providers if str(p.get("status") or "").lower() in {"online", "healthy"}]
    degraded_providers = [p for p in providers if str(p.get("status") or "").lower() == "degraded"]

    return {
        "agents": agents,
        "skills": skills,
        "cli_tools": cli_tools,
        "providers": providers,
        "summary": {
            "total_agents": len(agents),
            "enabled_agents": len([a for a in agents if a.get("is_enabled")]),
            "total_skills": len(skills),
            "online_providers": len(online_providers),
            "degraded_providers": len(degraded_providers),
        },
    }
