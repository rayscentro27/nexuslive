from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json
import os
import time


_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_TTL_SECONDS = int(os.getenv("HERMES_RUNTIME_CONFIG_CACHE_TTL_SECONDS", "45") or 45)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _env_truthy(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def _safe_select(path: str) -> list[dict[str, Any]]:
    try:
        from scripts.prelaunch_utils import rest_select

        return rest_select(path, timeout=8) or []
    except Exception:
        return []


def _cache_get(key: str) -> dict[str, Any] | None:
    row = _CACHE.get(key)
    if not row:
        return None
    expires_at, val = row
    if time.time() >= expires_at:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_set(key: str, val: dict[str, Any]) -> dict[str, Any]:
    _CACHE[key] = (time.time() + max(5, _TTL_SECONDS), val)
    return val


def default_runtime_config() -> dict[str, Any]:
    return {
        "hermes_personality": {
            "style": "operational_chief_of_staff",
            "tone": "concise_calm_direct",
            "internal_first": True,
            "long_output_channel": "email_report",
        },
        "hermes_internal_first_keywords": {
            "opencode": ["opencode", "codex", "what did codex finish"],
            "funding": ["funding blocker", "funding blockers", "funding"],
            "today": [
                "what should i work on today", "what should we work on today",
                "next best move", "what do you recommend we work on today",
                "what should i focus on today", "what to focus on today",
                "focus today", "priorities today", "top priorities",
            ],
            "knowledge_email": [
                "knowledge emails", "knowledge email", "what knowledge emails arrived",
                "knowledge intake", "intake status", "knowledge intake status",
                "summarize latest intake", "what knowledge arrived", "recent knowledge emails",
                "knowledge load", "what did we ingest",
            ],
            "marketing": ["what marketing research is pending", "marketing research", "marketing pending"],
            "travel": ["before travel", "travel", "remote ceo"],
            "notebooklm": [
                "what notebooklm research is ready", "summarize notebooklm intake queue", "notebooklm research",
                "notebooklm queue", "notebooklm status", "what's in notebooklm",
                "what is in notebooklm", "notebook research", "knowledge queue",
            ],
            "ai_providers": [
                "what ai providers are available", "ai providers available", "which ai providers",
                "model router status", "provider status", "provider routes",
                "is claude available", "is openrouter available", "is openclaw available",
                "is codex available", "did codex hit a rate limit", "what fallback provider",
                "available models", "which models are available", "what models can you use",
            ],
            "trading": [
                "trading status", "paper trading", "trading platform", "trading intelligence",
                "strategy status", "what strategies are running", "paper trades",
                "how is trading going", "trading update", "trading progress",
                "trading phase", "live trading", "trading safety", "trading mode",
            ],
            "circuit_breaker": [
                "circuit breaker", "circuit breakers", "circuit breaker status",
                "is trading halted", "halt status", "any circuit breakers",
                "trading halt", "kill switch",
            ],
        },
        "hermes_project_aliases": {
            "opencode": ["dev-agent bridge", "mac mini operational sessions", "ai ops dashboard"],
            "codex": ["implementation reports", "work sessions", "completion summaries"],
            "claude": ["claude cli tasks", "workspace context"],
            "funding": ["funding intelligence", "readiness scoring", "capital ladder"],
            "marketing": ["launch docs", "content calendar", "icp", "funnel"],
            "travel": ["remote readiness", "telegram status", "email status", "oracle access"],
        },
        "hermes_telegram_rules": {
            "mode": os.getenv("HERMES_TELEGRAM_MODE", "travel_mode").strip().lower(),
            "max_chars": 700,
            "allow_long": False,
        },
        "hermes_confidence_rules": {
            "stale_hours": 72,
            "labels": [
                "INTERNAL_CONFIRMED",
                "INTERNAL_PARTIAL",
                "INTERNAL_STALE",
                "GENERAL_FALLBACK",
                "NEEDS_RAYMOND_DECISION",
            ],
        },
    }


def load_runtime_config() -> dict[str, Any]:
    cache_key = "runtime_config"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    out = default_runtime_config()
    if not _env_truthy("HERMES_RUNTIME_CONFIG_SUPABASE_ENABLED", "true"):
        return _cache_set(cache_key, out)

    rows = _safe_select("hermes_runtime_config?select=config_key,config_value,enabled,updated_at&enabled=eq.true&limit=250")
    if not rows:
        return _cache_set(cache_key, out)

    for row in rows:
        key = str(row.get("config_key") or "").strip()
        if not key:
            continue
        val = row.get("config_value")
        if isinstance(val, dict):
            out[key] = val
        else:
            try:
                out[key] = json.loads(str(val))
            except Exception:
                out[key] = val
    return _cache_set(cache_key, out)


def get_telegram_mode() -> str:
    cfg = load_runtime_config().get("hermes_telegram_rules") or {}
    mode = str(cfg.get("mode") or "travel_mode").strip().lower()
    if mode not in {"travel_mode", "workstation_mode", "executive_mode", "incident_mode"}:
        return "travel_mode"
    return mode


def get_internal_first_keywords() -> dict[str, list[str]]:
    cfg = load_runtime_config().get("hermes_internal_first_keywords") or {}
    if not isinstance(cfg, dict):
        return default_runtime_config()["hermes_internal_first_keywords"]
    out: dict[str, list[str]] = {}
    for k, v in cfg.items():
        out[str(k)] = [str(x).lower() for x in (v or [])]
    return out


def format_telegram_reply(text: str) -> str:
    raw = str(text or "").strip()
    mode = get_telegram_mode()
    if mode == "workstation_mode":
        return raw[:1400]
    if mode == "executive_mode":
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return "\n".join(lines[:4])[:700]
    if mode == "incident_mode":
        return raw[:420]
    return raw[:700]
