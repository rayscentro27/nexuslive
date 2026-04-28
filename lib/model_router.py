"""
model_router.py — Tiered model routing for nexus-ai Python workers.

Agents call get_provider(task_type) instead of hardcoding provider URLs.
The router picks the cheapest capable provider and falls back up the chain.

Task types:
  embed    → HuggingFace (free, embeddings only)
  short    → Groq → NVIDIA NIM → OpenRouter     (< ~5K tokens)
  long     → Gemini Flash → OpenRouter           (> 10K tokens, 1M ctx free)
  draft    → Netcup Ollama → Oracle Ollama → OpenRouter   (background work)
  reason   → Hermes → OpenRouter                (structured reasoning)
  critical → Claude → OpenRouter                (highest quality)

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

# ── Provider environment ───────────────────────────────────────────────────────
_H_URL   = os.getenv("HERMES_GATEWAY_URL",  "http://127.0.0.1:8642")
_H_KEY   = os.getenv("HERMES_GATEWAY_KEY", "") or os.getenv("HERMES_GATEWAY_TOKEN", "")

_OR_URL  = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
_OR_KEY  = os.getenv("OPENROUTER_API_KEY",  "")
_OR_MDL  = os.getenv("OPENROUTER_MODEL",    "meta-llama/llama-3.3-70b-instruct")

_GQ_URL  = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
_GQ_KEY  = os.getenv("GROQ_API_KEY",  "")
_GQ_MDL  = "llama-3.3-70b-versatile"

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


def _chains() -> dict[str, list[dict]]:
    hermes   = {"name": "hermes",        "url": _H_URL,  "key": _H_KEY,  "model": "hermes", "format": "openai"}
    or70b    = {"name": "openrouter",    "url": _OR_URL, "key": _OR_KEY, "model": _OR_MDL,  "format": "openai"}
    groq     = {"name": "groq",          "url": _GQ_URL, "key": _GQ_KEY, "model": _GQ_MDL,  "format": "openai"}
    nvidia   = {"name": "nvidia_nim",    "url": _NV_URL, "key": _NV_KEY, "model": _NV_MDL,  "format": "openai"}
    gemini   = {"name": "gemini",        "url": _GM_URL, "key": _GM_KEY, "model": _GM_MDL,  "format": "openai"}
    claude   = {"name": "claude",        "url": _CL_URL, "key": _CL_KEY, "model": _CL_MDL,  "format": "anthropic"}
    oracle   = {"name": "oracle_ollama", "url": f"{_ORA_URL}/v1", "key": "", "model": _ORA_MDL, "format": "openai"}
    netcup   = {"name": "netcup_ollama", "url": _NC_BASE, "key": "",     "model": _NC_MDL,  "format": "ollama_generate"}

    return {
        "short":    [groq, nvidia, or70b, hermes, netcup],
        "long":     [gemini, or70b, hermes, netcup],
        "draft":    [netcup, oracle, or70b, hermes],
        "reason":   [hermes, or70b, claude],
        "critical": [claude, or70b, hermes],
    }


def get_provider(task_type: str = "draft", model_source: str = "auto") -> dict:
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
    chain = chains.get(task_type, chains["draft"])

    for provider in chain:
        name = provider["name"]
        key  = provider["key"]
        fmt  = provider["format"]

        # Local providers need no key; skip remote providers that lack one
        local = name in ("hermes", "netcup_ollama", "oracle_ollama")
        if not local and not _has_key(key):
            logger.debug("Skipping %s — no API key configured", name)
            continue

        # Skip Netcup if disabled
        if name == "netcup_ollama" and not _NC_ON:
            logger.debug("Skipping netcup_ollama — disabled by HERMES_FALLBACK_ENABLED")
            continue

        logger.debug("Selected provider: %s (task=%s)", name, task_type)
        return dict(provider)

    # Absolute last resort — Hermes without key check
    logger.warning("No configured provider found for task=%s; falling back to hermes", task_type)
    return {"name": "hermes", "url": _H_URL, "key": _H_KEY, "model": "hermes", "format": "openai"}


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


if __name__ == "__main__":
    import json, sys
    logging.basicConfig(level=logging.DEBUG)
    print("Provider summary:")
    for p in provider_summary():
        status = "OK" if p["configured"] else "NO KEY"
        print(f"  [{status:6}] {p['name']:<18} {p['url']}")
    print()
    for task in ("short", "long", "draft", "reason", "critical"):
        p = get_provider(task)
        print(f"  {task:<10} → {p['name']} ({p['model']})")
