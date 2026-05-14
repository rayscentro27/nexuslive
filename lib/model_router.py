"""
model_router.py — Tiered model routing for nexus-ai workers.

PROVIDER CLASSIFICATION
=======================
This router distinguishes auth-login providers from paid API providers.
Raymond primarily uses auth-login (subscription) tools, not metered APIs.

  AUTH-LOGIN providers (access_type: "auth_login"):
    chatgpt_auth_openclaw  — ChatGPT via OpenClaw local session proxy
                             cost_tier: included (flat subscription)
                             does NOT require OPENAI_API_KEY
    claude_auth_cli        — Claude via Claude Code / claude CLI
                             cost_tier: included (flat subscription)
                             does NOT require ANTHROPIC_API_KEY

  LOCAL providers (access_type: "local" or "remote_local"):
    hermes_local           — Hermes gateway on this machine
    netcup_ollama          — Ollama on Netcup ARM via SSH tunnel (localhost:11555)
    oracle_ollama          — Ollama on Oracle ARM direct (161.153.40.41:11434)

  API providers — PAID, not selected unless explicitly configured:
    openai_api             — OpenAI API (requires OPENAI_API_KEY + OPENAI_API_ENABLED=true)
    anthropic_api          — Anthropic API (requires ANTHROPIC_API_KEY + ANTHROPIC_API_ENABLED=true)
    openrouter_api         — OpenRouter (requires OPENROUTER_API_KEY)
    groq_api               — Groq (requires GROQ_API_KEY)
    gemini_api             — Google Gemini (requires GEMINI_API_KEY_*)
    nvidia_nim             — Nvidia NIM (requires NVIDIA_API_KEY)

ROUTING POLICY
==============
  telegram_reply:  chatgpt_auth_openclaw → netcup_ollama → groq_api
  coding:          claude_auth_cli → openrouter_api → chatgpt_auth_openclaw → openai_api
  cheap/summary:   netcup_ollama → oracle_ollama → chatgpt_auth_openclaw → groq_api
  reason/planning: hermes_local → openrouter_api → chatgpt_auth_openclaw

Task types:
  chat / cheap / planning / coding / reason / critical / short / long / draft
  cheap_summary / telegram_reply / funding_strategy / credit_analysis / grants_research

model_source shortcuts:
  "chatgpt_auth_openclaw"  "claude_auth_cli"  "openai_api"  "anthropic_api"
  "hermes_local" / "hermes"  "netcup_ollama"  "auto"
"""
from __future__ import annotations

import logging
import os
import shutil
import threading
import time
import urllib.request
from collections import deque
from typing import Deque

from lib.env_loader import load_nexus_env

load_nexus_env()

logger = logging.getLogger("ModelRouter")


# ── Rate limiter ───────────────────────────────────────────────────────────────

class _RateLimiter:
    """Sliding-window per-provider rate guard. Skips over-limit providers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, Deque[float]] = {}
        self._limits: dict[str, tuple[int, float]] = {
            "chatgpt_auth_openclaw": (120, 60.0),  # local proxy — generous
            "claude_auth_cli":       (60,  60.0),  # CLI subscription
            "groq_api":              (25,  60.0),  # Groq free: ~30 RPM
            "openrouter_api":        (40,  60.0),
            "gemini_api":            (10,  60.0),  # Gemini free: 15 RPM
            "nvidia_nim":            (20,  60.0),
            "openai_api":            (40,  60.0),
            "anthropic_api":         (40,  60.0),
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
            q = self._windows.setdefault(provider, deque())
            cutoff = time.monotonic() - window
            while q and q[0] < cutoff:
                q.popleft()
            return len(q) >= max_calls


_rate_limiter = _RateLimiter()


# ── AI-ops hooks (best-effort) ─────────────────────────────────────────────────

def _aiops_track_model_usage(task_type: str, provider: str, model: str, ok: bool) -> None:
    try:
        from lib.ai_ops_foundation import track_model_usage
        track_model_usage(task_type=task_type, provider=provider, model=model, duration_ms=0, ok=ok)
    except Exception:
        pass


def _aiops_track_retry(component: str, error_class: str, attempt: int, max_attempts: int) -> None:
    try:
        from lib.ai_ops_foundation import track_retry_event
        track_retry_event(component=component, error_class=error_class,
                          attempt=attempt, max_attempts=max_attempts)
    except Exception:
        pass


# ── Provider environment ───────────────────────────────────────────────────────

# Hermes local gateway
_H_URL  = os.getenv("HERMES_GATEWAY_URL",  "http://127.0.0.1:8642")
_H_KEY  = os.getenv("HERMES_GATEWAY_KEY", "") or os.getenv("HERMES_GATEWAY_TOKEN", "")

# OpenClaw — local ChatGPT auth-login proxy (NOT the OpenAI API)
_OC_URL  = os.getenv("OPENCLAW_URL",        "http://localhost:18789")
_OC_KEY  = os.getenv("OPENCLAW_AUTH_TOKEN", "") or os.getenv("OPENCLAW_API_KEY", "")
_OC_MDL  = os.getenv("OPENCLAW_MODEL",      "nousresearch/hermes-4-70b")
_OC_ON   = os.getenv("OPENCLAW_ENABLED",    "false").lower() not in ("false", "0", "no")

# Claude auth-login via claude CLI (NOT the Anthropic API)
_CA_BIN  = shutil.which("claude") or ""   # path to claude CLI binary
_CA_ON   = bool(_CA_BIN) and os.getenv("CLAUDE_AUTH_ENABLED", "true").lower() not in ("false", "0", "no")
_CA_MDL  = os.getenv("CLAUDE_AUTH_MODEL", "claude-sonnet-4-6")

# Ollama — Netcup via SSH tunnel
_NC_BASE = os.getenv("OLLAMA_FALLBACK_URL",   "http://localhost:11555/api/generate")
_NC_MDL  = os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.2:3b")
_NC_ON   = os.getenv("HERMES_FALLBACK_ENABLED", "true").lower() not in ("false", "0", "no")

# Ollama — Oracle ARM direct
_ORA_URL = os.getenv("OLLAMA_URL",   "http://161.153.40.41:11434")
_ORA_MDL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

# --- PAID API PROVIDERS — only selected when key present AND enabled flag set ---

_OR_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
_OR_KEY = os.getenv("OPENROUTER_API_KEY",  "")
_OR_MDL = os.getenv("OPENROUTER_MODEL",    "deepseek/deepseek-chat")

_GQ_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
_GQ_KEY = os.getenv("GROQ_API_KEY",  "")
_GQ_MDL = os.getenv("GROQ_MODEL",    "llama-3.1-8b-instant")

_NV_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
_NV_KEY = os.getenv("NVIDIA_API_KEY",  "")
_NV_MDL = "meta/llama-3.3-70b-instruct"

_GM_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
_GM_KEY = os.getenv("GEMINI_API_KEY_1", "") or os.getenv("GEMINI_API_KEY_2", "")
_GM_MDL = "gemini-1.5-flash"

# OpenAI API — PAID, requires key AND explicit enable flag (not set by default)
_OA_URL     = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
_OA_KEY     = os.getenv("OPENAI_API_KEY",  "")
_OA_MDL     = os.getenv("OPENAI_MODEL",    "gpt-4o-mini")
_OA_ENABLED = os.getenv("OPENAI_API_ENABLED", "false").lower() not in ("false", "0", "no")

# Anthropic API — PAID, requires key AND explicit enable flag (not set by default)
_CL_URL     = "https://api.anthropic.com/v1"
_CL_KEY     = os.getenv("ANTHROPIC_API_KEY", "")
_CL_MDL     = "claude-sonnet-4-6"
_CL_ENABLED = os.getenv("ANTHROPIC_API_ENABLED", "false").lower() not in ("false", "0", "no")


def _has_key(key: str) -> bool:
    return bool(key and key.strip())


# ── Provider factory ───────────────────────────────────────────────────────────

def _provider(
    provider_id:              str,
    display_name:             str,
    url:                      str,
    key:                      str,
    model:                    str,
    fmt:                      str,
    max_context:              int,
    cost_tier:                str,
    access_type:              str,
    requires_api_key:         bool,
    requires_login_session:   bool,
    requires_local_service:   bool,
    preferred_for:            list | None = None,
    fallback_rank:            int = 50,
    rate_limit_type:          str = "api_quota",
) -> dict:
    return {
        # Backwards-compatible fields (callers using p["name"] still work)
        "name":                    provider_id,
        "url":                     url,
        "key":                     key,
        "model":                   model,
        "format":                  fmt,
        "max_context":             max_context,
        "cost_tier":               cost_tier,
        # Enriched metadata
        "provider_id":             provider_id,
        "display_name":            display_name,
        "access_type":             access_type,
        "requires_api_key":        requires_api_key,
        "requires_login_session":  requires_login_session,
        "requires_local_service":  requires_local_service,
        "preferred_for":           preferred_for or [],
        "fallback_rank":           fallback_rank,
        "rate_limit_type":         rate_limit_type,
    }


class ModelRoutingError(ValueError):
    """Raised when no provider in the chain satisfies routing constraints."""


# ── Task classification ────────────────────────────────────────────────────────

MAIN_WORKFLOW_TASKS = frozenset({
    "premium_reasoning", "funding_strategy", "credit_analysis",
    "grants_research", "reason", "critical", "planning",
})

TASK_CLASS_ALIASES: dict[str, str] = {
    "funding_strategy":  "premium_reasoning",
    "credit_analysis":   "premium_reasoning",
    "telegram_reply":    "cheap_summary",
    "coding_assistant":  "coding",
    "research_worker":   "planning",
    "cheap_summary":     "cheap",
    "premium_reasoning": "reason",
}


def resolve_task_type(task_type: str) -> str:
    aliases = {"summary": "cheap", "classification": "cheap", "analysis": "planning",
               **TASK_CLASS_ALIASES}
    return aliases.get(task_type, task_type)


# ── Provider definitions & routing chains ─────────────────────────────────────

def _build_providers() -> dict[str, dict]:
    """Build all provider dicts. Called once per get_provider() invocation."""

    # ── Auth-login providers (subscription / included cost) ─────────────────

    chatgpt_auth = _provider(
        provider_id="chatgpt_auth_openclaw",
        display_name="ChatGPT auth-login via OpenClaw",
        url=f"{_OC_URL}/v1",
        key=_OC_KEY,
        model=_OC_MDL,
        fmt="openai",
        max_context=int(os.getenv("OPENCLAW_CTX", "128000")),
        cost_tier="included",
        access_type="auth_login",
        requires_api_key=False,
        requires_login_session=True,
        requires_local_service=True,
        preferred_for=["telegram_reply", "chat", "coding", "draft"],
        fallback_rank=10,
        rate_limit_type="subscription",
    )

    claude_auth = _provider(
        provider_id="claude_auth_cli",
        display_name="Claude Code auth-login (claude CLI)",
        url="",   # invoked as subprocess, not HTTP
        key="",
        model=_CA_MDL,
        fmt="cli_subprocess",
        max_context=int(os.getenv("CLAUDE_AUTH_CTX", "200000")),
        cost_tier="included",
        access_type="auth_login",
        requires_api_key=False,
        requires_login_session=True,
        requires_local_service=False,
        preferred_for=["coding", "code_review", "reason", "critical"],
        fallback_rank=5,
        rate_limit_type="subscription",
    )

    # ── Local providers (free, no external cost) ────────────────────────────

    hermes_local = _provider(
        provider_id="hermes_local",
        display_name="Hermes local gateway",
        url=_H_URL,
        key=_H_KEY,
        model="hermes",
        fmt="openai",
        max_context=int(os.getenv("HERMES_CTX", "65536")),
        cost_tier="free",
        access_type="local",
        requires_api_key=False,
        requires_login_session=False,
        requires_local_service=True,
        preferred_for=["reason", "funding_strategy", "credit_analysis"],
        fallback_rank=15,
        rate_limit_type="local_capacity",
    )

    netcup_ollama = _provider(
        provider_id="netcup_ollama",
        display_name="Netcup Ollama (SSH tunnel)",
        url=_NC_BASE,
        key="",
        model=_NC_MDL,
        fmt="ollama_generate",
        max_context=int(os.getenv("NETCUP_CTX", "8192")),
        cost_tier="free",
        access_type="remote_local",
        requires_api_key=False,
        requires_login_session=False,
        requires_local_service=True,
        preferred_for=["cheap", "cheap_summary", "draft"],
        fallback_rank=20,
        rate_limit_type="local_capacity",
    )

    oracle_ollama = _provider(
        provider_id="oracle_ollama",
        display_name="Oracle ARM Ollama (direct)",
        url=f"{_ORA_URL}/v1",
        key="",
        model=_ORA_MDL,
        fmt="openai",
        max_context=int(os.getenv("ORA_OLLAMA_CTX", "8192")),
        cost_tier="free",
        access_type="remote_local",
        requires_api_key=False,
        requires_login_session=False,
        requires_local_service=False,
        preferred_for=["cheap", "cheap_summary"],
        fallback_rank=25,
        rate_limit_type="local_capacity",
    )

    # ── Low-cost API providers ──────────────────────────────────────────────

    groq_api = _provider(
        provider_id="groq_api",
        display_name="Groq API",
        url=_GQ_URL,
        key=_GQ_KEY,
        model=_GQ_MDL,
        fmt="openai",
        max_context=int(os.getenv("GROQ_CTX", "10000")),
        cost_tier="low",
        access_type="api_key",
        requires_api_key=True,
        requires_login_session=False,
        requires_local_service=False,
        preferred_for=["short", "cheap_summary"],
        fallback_rank=35,
        rate_limit_type="api_quota",
    )

    nvidia_nim = _provider(
        provider_id="nvidia_nim",
        display_name="Nvidia NIM API",
        url=_NV_URL,
        key=_NV_KEY,
        model=_NV_MDL,
        fmt="openai",
        max_context=int(os.getenv("NVIDIA_CTX", "8192")),
        cost_tier="low",
        access_type="api_key",
        requires_api_key=True,
        requires_login_session=False,
        requires_local_service=False,
        preferred_for=["short"],
        fallback_rank=40,
        rate_limit_type="api_quota",
    )

    # ── Medium-cost API providers ───────────────────────────────────────────

    openrouter_api = _provider(
        provider_id="openrouter_api",
        display_name="OpenRouter API",
        url=_OR_URL,
        key=_OR_KEY,
        model=_OR_MDL,
        fmt="openai",
        max_context=int(os.getenv("OPENROUTER_CTX", "128000")),
        cost_tier="medium",
        access_type="api_key",
        requires_api_key=True,
        requires_login_session=False,
        requires_local_service=False,
        preferred_for=["planning", "coding", "premium_reasoning"],
        fallback_rank=45,
        rate_limit_type="api_quota",
    )

    gemini_api = _provider(
        provider_id="gemini_api",
        display_name="Gemini API",
        url=_GM_URL,
        key=_GM_KEY,
        model=_GM_MDL,
        fmt="openai",
        max_context=int(os.getenv("GEMINI_CTX", "1000000")),
        cost_tier="medium",
        access_type="api_key",
        requires_api_key=True,
        requires_login_session=False,
        requires_local_service=False,
        preferred_for=["planning", "long", "grants_research"],
        fallback_rank=48,
        rate_limit_type="api_quota",
    )

    # ── High-cost / paid API providers (disabled by default) ───────────────

    openai_api = _provider(
        provider_id="openai_api",
        display_name="OpenAI API (paid)",
        url=_OA_URL,
        key=_OA_KEY,
        model=_OA_MDL,
        fmt="openai",
        max_context=int(os.getenv("OPENAI_CTX", "128000")),
        cost_tier="high",
        access_type="api_key",
        requires_api_key=True,
        requires_login_session=False,
        requires_local_service=False,
        preferred_for=[],
        fallback_rank=90,
        rate_limit_type="api_quota",
    )

    anthropic_api = _provider(
        provider_id="anthropic_api",
        display_name="Anthropic API (paid)",
        url=_CL_URL,
        key=_CL_KEY,
        model="claude-sonnet-4-6",
        fmt="anthropic",
        max_context=int(os.getenv("CLAUDE_CTX", "200000")),
        cost_tier="high",
        access_type="api_key",
        requires_api_key=True,
        requires_login_session=False,
        requires_local_service=False,
        preferred_for=[],
        fallback_rank=95,
        rate_limit_type="api_quota",
    )

    return {
        "chatgpt_auth_openclaw": chatgpt_auth,
        "claude_auth_cli":       claude_auth,
        "hermes_local":          hermes_local,
        "netcup_ollama":         netcup_ollama,
        "oracle_ollama":         oracle_ollama,
        "groq_api":              groq_api,
        "nvidia_nim":            nvidia_nim,
        "openrouter_api":        openrouter_api,
        "gemini_api":            gemini_api,
        "openai_api":            openai_api,
        "anthropic_api":         anthropic_api,
    }


def _chains(providers: dict[str, dict]) -> dict[str, list[dict]]:
    p = providers  # shorthand

    return {
        # Telegram replies: ChatGPT auth first → local Ollama → API fallback
        "telegram_reply":    [p["chatgpt_auth_openclaw"], p["netcup_ollama"], p["oracle_ollama"],
                               p["groq_api"], p["openrouter_api"]],

        # Chat: auth-login first, then local, then cheap API
        "chat":              [p["chatgpt_auth_openclaw"], p["netcup_ollama"], p["groq_api"],
                               p["nvidia_nim"], p["openrouter_api"], p["hermes_local"]],

        # Coding: Claude CLI auth first → openrouter → ChatGPT auth → paid API last
        "coding":            [p["claude_auth_cli"], p["openrouter_api"],
                               p["chatgpt_auth_openclaw"], p["openai_api"],
                               p["hermes_local"], p["netcup_ollama"]],

        # Cheap / summaries: local Ollama first, then auth-login, then low-cost API
        "cheap":             [p["netcup_ollama"], p["oracle_ollama"],
                               p["chatgpt_auth_openclaw"], p["groq_api"], p["openrouter_api"]],

        # Cheap summary: same as cheap but shorter chain
        "cheap_summary":     [p["netcup_ollama"], p["oracle_ollama"],
                               p["chatgpt_auth_openclaw"], p["groq_api"]],

        # Draft: local Ollama first
        "draft":             [p["netcup_ollama"], p["oracle_ollama"],
                               p["chatgpt_auth_openclaw"], p["openrouter_api"], p["hermes_local"]],

        # Short quick answers: fast APIs, auth-login, local
        "short":             [p["groq_api"], p["nvidia_nim"], p["chatgpt_auth_openclaw"],
                               p["openrouter_api"], p["hermes_local"], p["netcup_ollama"]],

        # Long output: high-context providers
        "long":              [p["gemini_api"], p["openrouter_api"], p["hermes_local"], p["netcup_ollama"]],

        # Reasoning: Hermes internal first → auth-login → openrouter
        "reason":            [p["hermes_local"], p["chatgpt_auth_openclaw"],
                               p["claude_auth_cli"], p["openrouter_api"]],

        # Planning / large context: Gemini → openrouter → Claude auth → paid API
        "planning":          [p["gemini_api"], p["openrouter_api"], p["claude_auth_cli"],
                               p["hermes_local"], p["netcup_ollama"]],

        # Critical / safety: Claude auth first → openrouter → paid fallback
        "critical":          [p["claude_auth_cli"], p["openrouter_api"],
                               p["hermes_local"], p["anthropic_api"]],

        # Premium reasoning (funding/credit): hermes → openrouter → claude auth
        "premium_reasoning": [p["hermes_local"], p["openrouter_api"],
                               p["chatgpt_auth_openclaw"], p["claude_auth_cli"]],

        # Hermes-specific workflows
        "funding_strategy":  [p["hermes_local"], p["openrouter_api"],
                               p["chatgpt_auth_openclaw"], p["claude_auth_cli"]],
        "credit_analysis":   [p["hermes_local"], p["openrouter_api"],
                               p["chatgpt_auth_openclaw"], p["claude_auth_cli"]],
        "grants_research":   [p["gemini_api"], p["openrouter_api"],
                               p["claude_auth_cli"], p["chatgpt_auth_openclaw"]],
    }


# ── Provider selection ─────────────────────────────────────────────────────────

def get_provider(task_type: str = "draft", model_source: str = "auto", min_context: int = 0) -> dict:
    """
    Return the best available provider for the given task.

    Returns a dict with: name, url, key, model, format, max_context,
    cost_tier, provider_id, display_name, access_type, requires_api_key,
    requires_login_session, requires_local_service, preferred_for,
    fallback_rank, rate_limit_type.

    model_source shortcuts (bypass chain):
      "chatgpt_auth_openclaw"  — ChatGPT auth-login via OpenClaw
      "claude_auth_cli"        — Claude Code auth-login CLI
      "openai_api"             — OpenAI paid API (requires key)
      "anthropic_api"          — Anthropic paid API (requires key)
      "hermes_local" / "hermes" — Hermes local gateway
      "netcup_ollama"          — Netcup Ollama SSH tunnel
      "openclaw"               — alias for chatgpt_auth_openclaw
      "chatgpt"                — alias for openai_api
      "claude"                 — alias for anthropic_api
      "auto"                   — automatic chain selection (default)
    """
    providers = _build_providers()

    # ── model_source shortcuts ─────────────────────────────────────────────
    _shortcuts = {
        "openclaw": "chatgpt_auth_openclaw",
        "chatgpt":  "openai_api",
        "claude":   "anthropic_api",
    }
    model_source = _shortcuts.get(model_source, model_source)

    if model_source == "chatgpt_auth_openclaw":
        if not _OC_ON:
            logger.warning("chatgpt_auth_openclaw shortcut: OPENCLAW_ENABLED=false — falling to auto")
        else:
            return dict(providers["chatgpt_auth_openclaw"])

    if model_source == "claude_auth_cli":
        if not _CA_ON:
            logger.warning("claude_auth_cli shortcut: CLI not available or CLAUDE_AUTH_ENABLED=false — falling to auto")
        else:
            return dict(providers["claude_auth_cli"])

    if model_source == "openai_api":
        if not (_has_key(_OA_KEY) and _OA_ENABLED):
            logger.warning("openai_api shortcut: OPENAI_API_KEY not set or OPENAI_API_ENABLED=false — falling to auto")
        else:
            return dict(providers["openai_api"])

    if model_source == "anthropic_api":
        if not (_has_key(_CL_KEY) and _CL_ENABLED):
            logger.warning("anthropic_api shortcut: ANTHROPIC_API_KEY not set or ANTHROPIC_API_ENABLED=false — falling to auto")
        else:
            return dict(providers["anthropic_api"])

    if model_source in ("hermes_local", "hermes"):
        return dict(providers["hermes_local"])

    if model_source == "netcup_ollama":
        if not _NC_ON:
            logger.warning("netcup_ollama shortcut: HERMES_FALLBACK_ENABLED=false")
        return dict(providers["netcup_ollama"])

    # ── Auto chain selection ───────────────────────────────────────────────
    chains = _chains(providers)
    resolved_task = resolve_task_type(task_type)
    required_min_context = max(
        min_context,
        int(os.getenv("HERMES_MIN_CONTEXT_MAIN", "64000")) if resolved_task in MAIN_WORKFLOW_TASKS else min_context,
    )
    chain = chains.get(resolved_task, chains["draft"])

    for provider in chain:
        pid  = provider["provider_id"]
        key  = provider["key"]
        fmt  = provider["format"]

        # ── Per-provider availability gates ───────────────────────────────

        if pid == "netcup_ollama" and not _NC_ON:
            logger.debug("Skipping netcup_ollama — HERMES_FALLBACK_ENABLED=false")
            continue

        if pid == "chatgpt_auth_openclaw" and not _OC_ON:
            logger.debug("Skipping chatgpt_auth_openclaw — OPENCLAW_ENABLED=false")
            continue

        if pid == "claude_auth_cli" and not _CA_ON:
            logger.debug("Skipping claude_auth_cli — CLI not found or CLAUDE_AUTH_ENABLED=false")
            continue

        # OpenAI API: skip unless key present AND explicitly enabled
        if pid == "openai_api" and not (_has_key(_OA_KEY) and _OA_ENABLED):
            logger.debug("Skipping openai_api — key absent or OPENAI_API_ENABLED!=true")
            continue

        # Anthropic API: skip unless key present AND explicitly enabled
        if pid == "anthropic_api" and not (_has_key(_CL_KEY) and _CL_ENABLED):
            logger.debug("Skipping anthropic_api — key absent or ANTHROPIC_API_ENABLED!=true")
            continue

        # All other API providers: skip if no key
        is_local = provider["access_type"] in ("local", "remote_local", "auth_login")
        is_cli   = fmt == "cli_subprocess"
        if not is_local and not is_cli and not _has_key(key):
            logger.debug("Skipping %s — no API key configured", pid)
            continue

        # Context too small
        if required_min_context and int(provider.get("max_context", 0)) < required_min_context:
            logger.debug("Skipping %s — context %s < required %s",
                         pid, provider.get("max_context", 0), required_min_context)
            _aiops_track_retry("model_router", "context_too_small", 1, 1)
            continue

        # Rate limited
        if _rate_limiter.is_limited(pid):
            logger.warning("Skipping %s — rate limit reached", pid)
            _aiops_track_retry("model_router", "rate_limited", 1, 1)
            continue

        logger.debug("Selected: %s (%s) task=%s cost=%s",
                     pid, provider["display_name"], resolved_task, provider["cost_tier"])
        _rate_limiter.record(pid)
        _aiops_track_model_usage(task_type=resolved_task, provider=pid,
                                 model=str(provider.get("model") or "unknown"), ok=True)
        return dict(provider)

    _aiops_track_retry("model_router", "no_provider_satisfies_constraints", 1, 1)
    raise ModelRoutingError(
        f"No provider satisfies task={resolved_task} min_context={required_min_context}. "
        "All providers were unconfigured, disabled, rate-limited, or context too small."
    )


# ── Diagnostics ────────────────────────────────────────────────────────────────

def provider_summary() -> list[dict]:
    """Return full provider registry with availability status."""
    providers = _build_providers()
    result = []
    for pid, p in providers.items():
        configured = _provider_configured(pid, p)
        result.append({
            "name":                   pid,
            "provider_id":            pid,
            "display_name":           p["display_name"],
            "access_type":            p["access_type"],
            "cost_tier":              p["cost_tier"],
            "configured":             configured,
            "requires_api_key":       p["requires_api_key"],
            "requires_login_session": p["requires_login_session"],
            "requires_local_service": p["requires_local_service"],
            "preferred_for":          p["preferred_for"],
            "fallback_rank":          p["fallback_rank"],
            "rate_limit_type":        p["rate_limit_type"],
            "url":                    p["url"],
            "model":                  p["model"],
        })
    return result


def _provider_configured(pid: str, p: dict) -> bool:
    """Return True if the provider is usable in the current environment."""
    if pid == "chatgpt_auth_openclaw":
        return _OC_ON and (_has_key(_OC_KEY) or _OC_URL.startswith("http://localhost"))
    if pid == "claude_auth_cli":
        return _CA_ON
    if pid == "openai_api":
        return _has_key(_OA_KEY) and _OA_ENABLED
    if pid == "anthropic_api":
        return _has_key(_CL_KEY) and _CL_ENABLED
    if pid == "netcup_ollama":
        return _NC_ON
    if pid in ("hermes_local", "oracle_ollama"):
        return True   # always reachable (may time out if down, but not "unconfigured")
    return _has_key(p.get("key", ""))


def provider_status_report() -> str:
    """
    Return a Hermes-friendly human-readable status of all providers.

    Example output:
      Auth-login providers:
        ✅ ChatGPT auth-login via OpenClaw  [included]  chatgpt_auth_openclaw
        ✅ Claude Code auth-login (claude CLI)  [included]  claude_auth_cli
      Local providers:
        ✅ Hermes local gateway  [free]  hermes_local
        ✅ Netcup Ollama (SSH tunnel)  [free]  netcup_ollama
      API providers (paid — disabled by default):
        ⚪ OpenAI API (paid)  [high] — OPENAI_API_ENABLED=false
        ⚪ Anthropic API (paid)  [high] — ANTHROPIC_API_ENABLED=false
    """
    providers = _build_providers()
    lines = []
    by_type: dict[str, list] = {}
    for pid, p in providers.items():
        at = p["access_type"]
        by_type.setdefault(at, []).append((pid, p))

    type_labels = {
        "auth_login":    "Auth-login providers (subscription — no per-call cost):",
        "local":         "Local providers (no cost):",
        "remote_local":  "Remote-local providers (no cost):",
        "api_key":       "API providers (paid — skipped unless configured):",
    }

    for at in ("auth_login", "local", "remote_local", "api_key"):
        entries = by_type.get(at, [])
        if not entries:
            continue
        lines.append(type_labels.get(at, f"{at}:"))
        for pid, p in entries:
            ok = _provider_configured(pid, p)
            icon = "✅" if ok else "⚪"
            note = ""
            if pid == "openai_api" and not _OA_ENABLED:
                note = " — set OPENAI_API_ENABLED=true to enable"
            elif pid == "anthropic_api" and not _CL_ENABLED:
                note = " — set ANTHROPIC_API_ENABLED=true to enable"
            elif pid == "claude_auth_cli" and not _CA_BIN:
                note = " — claude CLI not found in PATH"
            lines.append(f"  {icon} {p['display_name']}  [{p['cost_tier']}]  {pid}{note}")

    return "\n".join(lines)


def routing_preview(task_type: str, min_context: int = 0) -> dict:
    """Return non-executing route metadata for diagnostics/tests."""
    resolved = resolve_task_type(task_type)
    provider = get_provider(task_type=task_type, model_source="auto", min_context=min_context)
    return {
        "requested_task":  task_type,
        "resolved_task":   resolved,
        "provider":        provider.get("name"),
        "display_name":    provider.get("display_name"),
        "access_type":     provider.get("access_type"),
        "cost_tier":       provider.get("cost_tier"),
        "model":           provider.get("model"),
        "max_context":     int(provider.get("max_context", 0) or 0),
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("=== Nexus Model Router — Provider Status ===\n")
    print(provider_status_report())
    print()

    print("=== Routing Preview ===")
    for task in ("telegram_reply", "chat", "cheap", "coding", "reason", "critical", "planning"):
        try:
            p = get_provider(task)
            print(f"  {task:<20} → {p['display_name']}  [{p['cost_tier']}]")
        except ModelRoutingError as e:
            print(f"  {task:<20} → ERROR: {e}")
