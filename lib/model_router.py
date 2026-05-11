"""
model_router.py — Tiered model routing for nexus-ai Python workers.

Agents call get_provider(task_type) instead of hardcoding provider URLs.
The router picks the cheapest capable provider and falls back up the chain.

Task types:
  chat     → fast conversational reply path
  cheap    → low-cost summaries/classification
  planning → large-context analysis
  coding   → code-focused routing
  reason   → executive/operator answers
  critical → highest-safety answers

model_source override (pass to get_provider):
  "hermes"        → Hermes gateway only
  "netcup_ollama" → Netcup Ollama directly
  "auto"          → default tier chain for task_type
"""
from __future__ import annotations

import logging
import os
import urllib.request

from lib.env_loader import load_nexus_env

load_nexus_env()

logger = logging.getLogger("ModelRouter")


def _aiops_track_model_usage(task_type: str, provider: str, model: str, ok: bool) -> None:
    try:
        from lib.ai_ops_foundation import track_model_usage
        track_model_usage(task_type=task_type, provider=provider, model=model, duration_ms=0, ok=ok)
    except Exception:
        pass


def _aiops_track_retry(component: str, error_class: str, attempt: int, max_attempts: int) -> None:
    try:
        from lib.ai_ops_foundation import track_retry_event
        track_retry_event(component=component, error_class=error_class, attempt=attempt, max_attempts=max_attempts)
    except Exception:
        pass

# ── Provider environment ───────────────────────────────────────────────────────
_H_URL   = os.getenv("HERMES_GATEWAY_URL",  "http://127.0.0.1:8642")
_H_KEY   = os.getenv("HERMES_GATEWAY_KEY", "") or os.getenv("HERMES_GATEWAY_TOKEN", "")

_OR_URL  = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
_OR_KEY  = os.getenv("OPENROUTER_API_KEY",  "")
_OR_MDL  = os.getenv("OPENROUTER_MODEL",    "deepseek/deepseek-chat")

_GQ_URL  = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
_GQ_KEY  = os.getenv("GROQ_API_KEY",  "")
_GQ_MDL  = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

_NV_URL  = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
_NV_KEY  = os.getenv("NVIDIA_API_KEY",  "")
_NV_MDL  = "meta/llama-3.3-70b-instruct"

_GM_URL  = "https://generativelanguage.googleapis.com/v1beta/openai"
_GM_KEY  = os.getenv("GEMINI_API_KEY_1", "") or os.getenv("GEMINI_API_KEY_2", "")
_GM_MDL  = "gemini-1.5-flash"

_CL_URL  = "https://api.anthropic.com/v1"
_CL_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
_CL_MDL  = "claude-sonnet-4-6"

_ORA_URL  = os.getenv("OLLAMA_URL", "http://161.153.40.41:11434")
_ORA_MDL  = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

_NC_BASE  = os.getenv("OLLAMA_FALLBACK_URL", "http://localhost:11555/api/generate")
_NC_MDL   = os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.2:3b")
_NC_ON    = os.getenv("HERMES_FALLBACK_ENABLED", "true").lower() not in ("false", "0", "no")


def _has_key(key: str) -> bool:
    return bool(key and key.strip())


def _provider(name: str, url: str, key: str, model: str, fmt: str, max_context: int) -> dict:
    return {
        "name": name,
        "url": url,
        "key": key,
        "model": model,
        "format": fmt,
        "max_context": max_context,
    }


class ModelRoutingError(ValueError):
    """Raised when no provider satisfies safety routing constraints."""


MAIN_WORKFLOW_TASKS = frozenset({
    "premium_reasoning",
    "funding_strategy",
    "credit_analysis",
    "grants_research",
    "reason",
    "critical",
    "planning",
})


TASK_CLASS_ALIASES: dict[str, str] = {
    "funding_strategy": "premium_reasoning",
    "credit_analysis": "premium_reasoning",
    "telegram_reply": "cheap_summary",
    "coding_assistant": "coding",
    "research_worker": "planning",
    "cheap_summary": "cheap",
    "premium_reasoning": "reason",
}


def resolve_task_type(task_type: str) -> str:
    """Resolve external task classes into router-native task types."""
    aliases = {
        "summary": "cheap",
        "classification": "cheap",
        "analysis": "planning",
        **TASK_CLASS_ALIASES,
    }
    return aliases.get(task_type, task_type)


def _chains() -> dict[str, list[dict]]:
    hermes   = _provider("hermes", _H_URL, _H_KEY, "hermes", "openai", int(os.getenv("HERMES_CTX", "65536")))
    or70b    = _provider("openrouter", _OR_URL, _OR_KEY, _OR_MDL, "openai", int(os.getenv("OPENROUTER_CTX", "128000")))
    groq     = _provider("groq", _GQ_URL, _GQ_KEY, _GQ_MDL, "openai", int(os.getenv("GROQ_CTX", "10000")))
    nvidia   = _provider("nvidia_nim", _NV_URL, _NV_KEY, _NV_MDL, "openai", int(os.getenv("NVIDIA_CTX", "8192")))
    gemini   = _provider("gemini", _GM_URL, _GM_KEY, _GM_MDL, "openai", int(os.getenv("GEMINI_CTX", "1000000")))
    claude   = _provider("claude", _CL_URL, _CL_KEY, _CL_MDL, "anthropic", int(os.getenv("CLAUDE_CTX", "200000")))
    oracle   = _provider("oracle_ollama", f"{_ORA_URL}/v1", "", _ORA_MDL, "openai", int(os.getenv("ORA_OLLAMA_CTX", "8192")))
    netcup   = _provider("netcup_ollama", _NC_BASE, "", _NC_MDL, "ollama_generate", int(os.getenv("NETCUP_CTX", "8192")))

    return {
        "chat":     [netcup, groq, nvidia, or70b, hermes],
        "cheap":    [netcup, oracle, groq, or70b],
        "planning": [gemini, or70b, claude, hermes, netcup],
        "coding":   [or70b, claude, hermes, netcup],
        "short":    [groq, nvidia, or70b, hermes, netcup],
        "long":     [gemini, or70b, hermes, netcup],
        "draft":    [netcup, oracle, or70b, hermes],
        "reason":   [hermes, or70b, claude],
        "critical": [claude, or70b, hermes],
        "premium_reasoning": [or70b, claude, hermes],
        "cheap_summary": [netcup, oracle, groq],
        "telegram_reply": [or70b, groq, netcup],
        "funding_strategy": [or70b, claude, hermes],
        "credit_analysis": [or70b, claude, hermes],
        "grants_research": [gemini, or70b, claude],
    }


def get_provider(task_type: str = "draft", model_source: str = "auto", min_context: int = 0) -> dict:
    """
    Return the best configured provider for the given task.

    Returns a dict: {name, url, key, model, format}
    format is one of: "openai" | "ollama_generate" | "anthropic"
    """
    if model_source == "netcup_ollama":
        if not _NC_ON:
            logger.warning("netcup_ollama requested but HERMES_FALLBACK_ENABLED=false")
        return {"name": "netcup_ollama", "url": _NC_BASE, "key": "", "model": _NC_MDL, "format": "ollama_generate"}

    if model_source == "hermes":
        return {"name": "hermes", "url": _H_URL, "key": _H_KEY, "model": "hermes", "format": "openai"}

    chains = _chains()
    resolved_task = resolve_task_type(task_type)
    required_min_context = max(min_context, int(os.getenv("HERMES_MIN_CONTEXT_MAIN", "64000")) if resolved_task in MAIN_WORKFLOW_TASKS else min_context)
    chain = chains.get(resolved_task, chains["draft"])

    for provider in chain:
        name = provider["name"]
        key  = provider["key"]
        fmt  = provider["format"]

        # Local providers need no key; skip remote providers that lack one
        local = name in ("hermes", "netcup_ollama", "oracle_ollama")
        if not local and not _has_key(key):
            logger.debug("Skipping %s — no API key configured", name)
            continue

        if required_min_context and int(provider.get("max_context", 0)) < required_min_context:
            logger.debug(
                "Skipping %s — context too small (%s < %s)",
                name,
                provider.get("max_context", 0),
                required_min_context,
            )
            _aiops_track_retry("model_router", "context_too_small", 1, 1)
            continue

        # Skip Netcup if disabled
        if name == "netcup_ollama" and not _NC_ON:
            logger.debug("Skipping netcup_ollama — disabled by HERMES_FALLBACK_ENABLED")
            continue

        logger.debug("Selected provider: %s (task=%s, min_ctx=%s)", name, resolved_task, required_min_context)
        _aiops_track_model_usage(
            task_type=resolved_task,
            provider=name,
            model=str(provider.get("model") or "unknown"),
            ok=True,
        )
        return dict(provider)

    _aiops_track_retry("model_router", "no_provider_satisfies_constraints", 1, 1)
    raise ModelRoutingError(
        f"No provider satisfies task={resolved_task} with minimum context {required_min_context}. "
        "Hermes paused this task because the selected model context is too small."
    )


def provider_summary() -> list[dict]:
    """Return all providers with their configuration status (for diagnostics)."""
    return [
        {"name": "hermes",        "configured": _has_key(_H_KEY),  "url": _H_URL},
        {"name": "openrouter",    "configured": _has_key(_OR_KEY), "url": _OR_URL},
        {"name": "groq",          "configured": _has_key(_GQ_KEY), "url": _GQ_URL},
        {"name": "nvidia_nim",    "configured": _has_key(_NV_KEY), "url": _NV_URL},
        {"name": "gemini",        "configured": _has_key(_GM_KEY), "url": _GM_URL},
        {"name": "claude",        "configured": _has_key(_CL_KEY), "url": _CL_URL},
        {"name": "oracle_ollama", "configured": True,               "url": _ORA_URL},
        {"name": "netcup_ollama", "configured": _NC_ON,            "url": _NC_BASE},
    ]


def routing_preview(task_type: str, min_context: int = 0) -> dict:
    """Return non-executing route metadata for diagnostics/tests."""
    resolved = resolve_task_type(task_type)
    provider = get_provider(task_type=task_type, model_source="auto", min_context=min_context)
    return {
        "requested_task": task_type,
        "resolved_task": resolved,
        "provider": provider.get("name"),
        "model": provider.get("model"),
        "max_context": int(provider.get("max_context", 0) or 0),
    }


if __name__ == "__main__":
    import json, sys
    logging.basicConfig(level=logging.DEBUG)
    print("Provider summary:")
    for p in provider_summary():
        status = "OK" if p["configured"] else "NO KEY"
        print(f"  [{status:6}] {p['name']:<18} {p['url']}")
    print()
    for task in ("chat", "cheap", "planning", "coding", "reason", "critical"):
        p = get_provider(task)
        print(f"  {task:<10} → {p['name']} ({p['model']})")
