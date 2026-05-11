"""
model_router.py — Tiered model routing for nexus-ai Python workers.

Agents call get_provider(task_type) instead of hardcoding provider URLs.
The router picks the cheapest capable provider and falls back up the chain.

Routing order (cheapest/local first):
  Hermes local → Netcup Ollama (SSH tunnel) → Oracle Ollama (direct ARM)
  → OpenClaw (local ChatGPT proxy) → Groq → Nvidia NIM → OpenRouter
  → Gemini → Claude → ChatGPT

Task types:
  chat     → fast conversational reply
  cheap    → low-cost summaries/classification
  planning → large-context analysis
  coding   → code-focused routing
  reason   → executive/operator answers
  critical → highest-safety answers

model_source override (pass to get_provider):
  "hermes"        → Hermes gateway only
  "netcup_ollama" → Netcup Ollama (SSH tunnel) directly
  "openclaw"      → OpenClaw local ChatGPT proxy directly
  "chatgpt"       → OpenAI ChatGPT directly
  "auto"          → default tier chain for task_type

Cost tiers (per provider dict):
  "free"    → local models, no API cost
  "low"     → Groq free tier, OpenRouter cheap models
  "medium"  → OpenRouter premium, Nvidia NIM, Gemini
  "high"    → Claude Sonnet/Opus, ChatGPT GPT-4, OpenRouter frontier
"""
from __future__ import annotations

import logging
import os
import time
import threading
import urllib.request
from collections import deque
from typing import Deque

from lib.env_loader import load_nexus_env

load_nexus_env()

logger = logging.getLogger("ModelRouter")


# ── Rate limiter ───────────────────────────────────────────────────────────────

class _RateLimiter:
    """
    Sliding-window rate limiter per provider.
    Thread-safe; used inside get_provider() to skip over-limit providers.
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # provider_name → deque of call timestamps (float)
        self._windows: dict[str, Deque[float]] = {}
        # provider_name → (max_calls, window_seconds)
        self._limits: dict[str, tuple[int, float]] = {
            "groq":        (25,  60.0),   # Groq free: ~30 RPM
            "openrouter":  (40,  60.0),   # OpenRouter free: 50 RPM
            "gemini":      (10,  60.0),   # Gemini free: 15 RPM
            "nvidia_nim":  (20,  60.0),
            "claude":      (40,  60.0),
            "chatgpt":     (40,  60.0),
            "openclaw":    (100, 60.0),   # Local proxy — generous limit
        }

    def record(self, provider: str) -> None:
        with self._lock:
            if provider not in self._windows:
                self._windows[provider] = deque()
            self._windows[provider].append(time.monotonic())

    def is_limited(self, provider: str) -> bool:
        if provider not in self._limits:
            return False
        max_calls, window = self._limits[provider]
        with self._lock:
            q = self._windows.get(provider, deque())
            cutoff = time.monotonic() - window
            # Prune expired entries
            while q and q[0] < cutoff:
                q.popleft()
            return len(q) >= max_calls


_rate_limiter = _RateLimiter()


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

# Netcup Ollama — accessed via SSH tunnel (ssh -N -L 11555:localhost:11434 root@NETCUP_IP)
_NC_BASE  = os.getenv("OLLAMA_FALLBACK_URL", "http://localhost:11555/api/generate")
_NC_MDL   = os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.2:3b")
_NC_ON    = os.getenv("HERMES_FALLBACK_ENABLED", "true").lower() not in ("false", "0", "no")

# OpenClaw — local ChatGPT proxy (OpenAI-compatible API at localhost)
# Use: OPENCLAW_URL, OPENCLAW_AUTH_TOKEN, OPENCLAW_MODEL
_OC_URL   = os.getenv("OPENCLAW_URL",        "http://localhost:18789")
_OC_KEY   = os.getenv("OPENCLAW_AUTH_TOKEN", "") or os.getenv("OPENCLAW_API_KEY", "")
_OC_MDL   = os.getenv("OPENCLAW_MODEL",      "nousresearch/hermes-4-70b")
_OC_ON    = os.getenv("OPENCLAW_ENABLED",    "true").lower() not in ("false", "0", "no")

# ChatGPT / OpenAI direct
_OA_URL   = os.getenv("OPENAI_BASE_URL",  "https://api.openai.com/v1")
_OA_KEY   = os.getenv("OPENAI_API_KEY",   "")
_OA_MDL   = os.getenv("OPENAI_MODEL",     "gpt-4o-mini")


def _has_key(key: str) -> bool:
    return bool(key and key.strip())


def _provider(name: str, url: str, key: str, model: str, fmt: str, max_context: int, cost_tier: str = "medium") -> dict:
    return {
        "name":       name,
        "url":        url,
        "key":        key,
        "model":      model,
        "format":     fmt,
        "max_context": max_context,
        "cost_tier":  cost_tier,   # "free" | "low" | "medium" | "high"
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
    # Local / free providers (no API cost)
    hermes   = _provider("hermes",        _H_URL,          _H_KEY,  "hermes",               "openai",          int(os.getenv("HERMES_CTX",      "65536")),  "free")
    netcup   = _provider("netcup_ollama", _NC_BASE,         "",      _NC_MDL,               "ollama_generate", int(os.getenv("NETCUP_CTX",      "8192")),   "free")
    oracle   = _provider("oracle_ollama", f"{_ORA_URL}/v1", "",      _ORA_MDL,              "openai",          int(os.getenv("ORA_OLLAMA_CTX",  "8192")),   "free")
    openclaw = _provider("openclaw",      f"{_OC_URL}/v1",  _OC_KEY, _OC_MDL,               "openai",          int(os.getenv("OPENCLAW_CTX",    "128000")), "free")

    # Low-cost cloud providers
    groq     = _provider("groq",          _GQ_URL,          _GQ_KEY, _GQ_MDL,               "openai",          int(os.getenv("GROQ_CTX",        "10000")),  "low")
    nvidia   = _provider("nvidia_nim",    _NV_URL,          _NV_KEY, _NV_MDL,               "openai",          int(os.getenv("NVIDIA_CTX",      "8192")),   "low")

    # Medium-cost cloud providers
    or70b    = _provider("openrouter",    _OR_URL,          _OR_KEY, _OR_MDL,               "openai",          int(os.getenv("OPENROUTER_CTX",  "128000")), "medium")
    gemini   = _provider("gemini",        _GM_URL,          _GM_KEY, _GM_MDL,               "openai",          int(os.getenv("GEMINI_CTX",      "1000000")),"medium")
    chatgpt  = _provider("chatgpt",       _OA_URL,          _OA_KEY, _OA_MDL,               "openai",          int(os.getenv("OPENAI_CTX",      "128000")), "high")

    # High-cost / frontier providers
    claude   = _provider("claude",        _CL_URL,          _CL_KEY, _CL_MDL,               "anthropic",       int(os.getenv("CLAUDE_CTX",      "200000")), "high")

    # Routing chains — cheapest/local first, escalate to paid on failure
    return {
        # Fast chat: local → openclaw → groq → openrouter → hermes
        "chat":              [netcup, openclaw, groq, nvidia, or70b, hermes],
        # Cheap summaries: local models only, no spend
        "cheap":             [netcup, oracle, openclaw, groq, or70b],
        # Long-context planning: gemini (1M ctx) → openrouter → claude
        "planning":          [gemini, or70b, claude, hermes, netcup],
        # Code tasks: openrouter → openclaw (ChatGPT path) → claude → hermes
        "coding":            [or70b, openclaw, chatgpt, claude, hermes, netcup],
        # Short quick answers: groq → nvidia → openrouter → hermes
        "short":             [groq, nvidia, openclaw, or70b, hermes, netcup],
        # Long output: gemini → openrouter → hermes
        "long":              [gemini, or70b, hermes, netcup],
        # Draft generation: local first, then cheap cloud
        "draft":             [netcup, oracle, openclaw, or70b, hermes],
        # Reasoning: hermes internal first → openrouter → claude
        "reason":            [hermes, or70b, openclaw, claude],
        # Critical / safety-sensitive: claude → openrouter → hermes
        "critical":          [claude, or70b, hermes],
        # Premium reasoning (funding/credit workflows): openrouter → claude
        "premium_reasoning": [or70b, claude, hermes],
        # Cheap summary: local only
        "cheap_summary":     [netcup, oracle, openclaw, groq],
        # Telegram replies: fast and cheap
        "telegram_reply":    [openclaw, or70b, groq, netcup],
        # Hermes-specific workflows: always hermes first
        "funding_strategy":  [hermes, or70b, openclaw, claude],
        "credit_analysis":   [hermes, or70b, openclaw, claude],
        "grants_research":   [gemini, or70b, claude],
    }


def get_provider(task_type: str = "draft", model_source: str = "auto", min_context: int = 0) -> dict:
    """
    Return the best configured provider for the given task.

    Returns a dict: {name, url, key, model, format, max_context, cost_tier}
    format is one of: "openai" | "ollama_generate" | "anthropic"

    model_source shortcuts bypass the chain:
      "netcup_ollama" → Netcup SSH-tunnel Ollama
      "hermes"        → Hermes gateway
      "openclaw"      → OpenClaw local ChatGPT proxy
      "chatgpt"       → OpenAI direct
      "auto"          → chain selection (default)
    """
    if model_source == "netcup_ollama":
        if not _NC_ON:
            logger.warning("netcup_ollama requested but HERMES_FALLBACK_ENABLED=false")
        return {"name": "netcup_ollama", "url": _NC_BASE, "key": "", "model": _NC_MDL,
                "format": "ollama_generate", "max_context": 8192, "cost_tier": "free"}

    if model_source == "hermes":
        return {"name": "hermes", "url": _H_URL, "key": _H_KEY, "model": "hermes",
                "format": "openai", "max_context": 65536, "cost_tier": "free"}

    if model_source == "openclaw":
        if not _OC_ON:
            logger.warning("openclaw requested but OPENCLAW_ENABLED=false — falling through to auto")
        else:
            return {"name": "openclaw", "url": f"{_OC_URL}/v1", "key": _OC_KEY, "model": _OC_MDL,
                    "format": "openai", "max_context": 128000, "cost_tier": "free"}

    if model_source == "chatgpt":
        if not _has_key(_OA_KEY):
            logger.warning("chatgpt requested but OPENAI_API_KEY not set — falling through to auto")
        else:
            return {"name": "chatgpt", "url": _OA_URL, "key": _OA_KEY, "model": _OA_MDL,
                    "format": "openai", "max_context": 128000, "cost_tier": "high"}

    chains = _chains()
    resolved_task = resolve_task_type(task_type)
    required_min_context = max(
        min_context,
        int(os.getenv("HERMES_MIN_CONTEXT_MAIN", "64000")) if resolved_task in MAIN_WORKFLOW_TASKS else min_context,
    )
    chain = chains.get(resolved_task, chains["draft"])

    for provider in chain:
        name = provider["name"]
        key  = provider["key"]

        # Gate: disabled providers
        if name == "netcup_ollama" and not _NC_ON:
            logger.debug("Skipping netcup_ollama — disabled by HERMES_FALLBACK_ENABLED")
            continue
        if name == "openclaw" and not _OC_ON:
            logger.debug("Skipping openclaw — disabled by OPENCLAW_ENABLED")
            continue

        # Gate: remote providers without a configured key
        local = name in ("hermes", "netcup_ollama", "oracle_ollama", "openclaw")
        if not local and not _has_key(key):
            logger.debug("Skipping %s — no API key configured", name)
            continue

        # Gate: context too small for this task
        if required_min_context and int(provider.get("max_context", 0)) < required_min_context:
            logger.debug(
                "Skipping %s — context %s < required %s",
                name, provider.get("max_context", 0), required_min_context,
            )
            _aiops_track_retry("model_router", "context_too_small", 1, 1)
            continue

        # Gate: rate limited
        if _rate_limiter.is_limited(name):
            logger.warning("Skipping %s — rate limit reached, trying next provider", name)
            _aiops_track_retry("model_router", "rate_limited", 1, 1)
            continue

        logger.debug(
            "Selected provider: %s model=%s task=%s cost=%s",
            name, provider.get("model"), resolved_task, provider.get("cost_tier"),
        )
        _rate_limiter.record(name)
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
        "All providers in chain were either unconfigured, rate-limited, or context too small."
    )


def provider_summary() -> list[dict]:
    """Return all providers with configuration status and cost tier (for diagnostics)."""
    return [
        # Local / free
        {"name": "hermes",        "configured": True,              "cost_tier": "free",   "url": _H_URL,   "note": "local Hermes gateway"},
        {"name": "netcup_ollama", "configured": _NC_ON,            "cost_tier": "free",   "url": _NC_BASE, "note": "SSH tunnel to Netcup ARM"},
        {"name": "oracle_ollama", "configured": True,              "cost_tier": "free",   "url": _ORA_URL, "note": "Oracle ARM direct (161.153.40.41)"},
        {"name": "openclaw",      "configured": _OC_ON and (_has_key(_OC_KEY) or _OC_URL.startswith("http://localhost")),
                                                                    "cost_tier": "free",   "url": _OC_URL,  "note": "local ChatGPT proxy"},
        # Low cost
        {"name": "groq",          "configured": _has_key(_GQ_KEY), "cost_tier": "low",    "url": _GQ_URL,  "note": "free tier ~30 RPM"},
        {"name": "nvidia_nim",    "configured": _has_key(_NV_KEY), "cost_tier": "low",    "url": _NV_URL,  "note": "llama-3.3-70b"},
        # Medium cost
        {"name": "openrouter",    "configured": _has_key(_OR_KEY), "cost_tier": "medium", "url": _OR_URL,  "note": "multi-model marketplace"},
        {"name": "gemini",        "configured": _has_key(_GM_KEY), "cost_tier": "medium", "url": _GM_URL,  "note": "1M context window"},
        # High cost / frontier
        {"name": "chatgpt",       "configured": _has_key(_OA_KEY), "cost_tier": "high",   "url": _OA_URL,  "note": "OpenAI direct"},
        {"name": "claude",        "configured": _has_key(_CL_KEY), "cost_tier": "high",   "url": _CL_URL,  "note": "Anthropic Sonnet"},
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
