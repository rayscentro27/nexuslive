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
            "opencode": [
                "opencode", "codex", "what did codex finish",
                "what did claude code finish", "what did claude code complete",
            ],
            "claude_code_work": [
                "what did claude code work on", "what did claude work on",
                "what did claude code do", "claude code session", "claude code work",
                "what was built yesterday", "what happened yesterday", "yesterday's progress",
                "what was completed yesterday", "show handoffs", "claude handoffs",
                "recent handoffs", "latest handoff", "what did claude build",
            ],
            "funding": ["funding blocker", "funding blockers", "show funding", "what are my funding blockers"],
            "create_content_draft": [
                "create the first draft", "create first draft", "build checklist draft",
                "draft lead magnet", "create the checklist", "build the checklist",
                "create a new version of the checklist", "revise the checklist",
            ],
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
                "list notebooklm notebooks", "sync forex notebook", "sync all enabled notebooks",
                "what did notebooklm learn", "show notebook sync status", "pending review",
                "summarize the grants notebook", "what trading strategies came from notebooklm",
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
                "paper results", "paper performance", "how did paper", "best session",
                "best time to trade", "session performance", "when to trade",
                "active strategy", "what strategy", "which strategy", "strategy running",
                "is demo safe", "is paper safe", "safety status",
                "why paused", "why halted", "why stopped", "what paused",
                "why is trading paused", "why is trading halted", "is trading paused",
            ],
            "circuit_breaker": [
                "circuit breaker", "circuit breakers", "circuit breaker status",
                "is trading halted", "halt status", "any circuit breakers",
                "trading halt", "kill switch",
            ],
            "workforce": [
                "workforce status", "worker status", "workforce report",
                "which workers are active", "worker productivity", "worker performance",
                "who is working", "what are the workers doing", "worker activity",
                "ai workforce", "workforce health", "team status",
                "which workers are idle", "which workers failed", "inactive workers",
            ],
            "ceo_briefing": [
                "ceo briefing", "morning briefing", "daily briefing", "operational briefing",
                "generate briefing", "what's the briefing", "ceo report", "morning report",
                "operational report", "daily report", "executive briefing",
                "give me the briefing", "run the briefing", "today's briefing",
            ],
            "claw3d": [
                "claw3d", "claw 3d", "3d office", "virtual office", "agent office",
                "open the office", "start the office", "office status",
                "claw3d status", "claw3d start", "is claw3d running", "launch office",
                "3d workspace", "visual office",
            ],
            "evidence": [
                "evidence guard", "false completion", "false completions",
                "evidence status", "are there false completions", "audit completions",
                "show false completions", "evidence audit", "completion audit",
                "which tasks lack evidence", "evidence report",
            ],
            "improvement": [
                "improvement queue", "autonomous improvement", "what are workers improving",
                "idle tasks", "background tasks", "what is nexus doing", "auto improve",
                "improvement status", "what is improving", "improvement worker",
                "proactive tasks", "nexus background work",
            ],
            "executive_memory": [
                "executive memory", "hermes memory", "operational memory",
                "what does hermes know", "what is hermes tracking", "hermes context",
                "show memory", "memory status", "what's in memory",
                "show operational context", "what is nexus tracking",
            ],
            "execution_priorities": [
                "what are the priorities", "today's priorities", "top priorities today",
                "what should we do today", "daily priorities", "what should i focus on",
                "current priorities", "priority list", "what's priority one",
                "top 3 priorities", "highest priority", "critical priorities",
                "what needs doing", "what's most urgent", "urgent priorities",
                "what should we focus on today", "what should i focus on today",
                "what do we focus on", "what to focus on today", "focus today",
                "current focus", "what is the focus", "execution priorities",
                "show execution priorities", "top priority",
            ],
            "monetization": [
                "monetization priorities", "affiliate campaigns",
                "what affiliates are active", "revenue levers", "show affiliates",
                "how do we make money", "revenue priorities", "how is monetization",
                "affiliate status", "income strategy", "business goals",
                "what are the business goals", "current goals",
                "revenue progress", "how much have we made", "$1000 goal",
                "weekly revenue", "revenue target",
            ],
            "scouts": [
                "what scouts are running", "intelligence scouts",
                "which scouts ran", "scout productivity", "market intelligence scouts",
                "monetization scouts", "scout registry",
                "what scouts are active", "consensus engine", "run consensus",
                "opportunity rankings", "ranked opportunities",
            ],
            "watchers": [
                "watcher status", "what watchers are running", "watcher loop",
                "intelligence watchers", "are watchers running", "monitoring status",
                "content trends", "affiliate watcher", "seo watcher",
                "funding watcher", "trading watcher",
            ],
            "source_intelligence": [
                "youtube intelligence", "source intelligence", "what sources are registered",
                "intelligence sources", "show sources", "source extractions",
                "what did the scouts extract", "intelligence summary", "daily intelligence",
                "source findings", "youtube scout findings", "latest intel",
                "what intelligence is available", "channel intelligence",
                "jj simon", "the one lance b", "cal barton", "koerner office",
                "codeglitch", "ai rush minutes", "luuk alleman", "stedman waiters",
            ],
            "information_sources": [
                "where do you get your information", "what are your sources",
                "information sources", "where does this data come from",
                "what data sources do you use", "where does your information come from",
                "how do you know that", "where did you get that", "what is your source",
                "how do you get your data", "what files do you read", "what do you read",
                "where do you read from", "hermes data sources",
                "what did you get your information from", "where did you get your information",
                "what information did you use", "where did that come from",
            ],
            "nexus_project": [
                "what is nexus", "what is the nexus project", "nexus overview",
                "tell me about nexus", "nexus mission", "what does nexus do",
                "describe nexus", "nexus platform", "nexus project brief",
                "what is nexus trying to do", "nexus goals", "what is nexus building",
            ],
            "goals_30_day": [
                "30 day goals", "30 day plan", "30-day goals", "30-day plan",
                "what is the 30 day plan", "monthly goals", "month goals",
                "what are the 30 day goals", "show the 30 day plan",
                "this month's plan", "monthly revenue plan", "revenue plan",
                "30 day revenue", "what's the plan for this month",
                "what is the monthly target", "monthly target",
            ],
            "youtube_status": [
                "youtube status", "youtube intake", "youtube sources",
                "what youtube sources", "source intake status", "intake status",
                "what videos are registered", "youtube registry",
                "what youtube videos", "registered videos", "show youtube intake",
                "last youtube channel that was processed", "what youtube channel",
                "youtube channels registered",
            ],
            "trading_recommendation": [
                "what trading strategy do you recommend",
                "what forex strategy should we test",
                "what is the best strategy so far",
                "what should we paper trade",
                "what should we test on oanda demo",
                "what did vibe-trading learn",
                "what did vibe trading learn",
                "what is the best backtest result",
                "what trading strategy improved",
                "show backtest results",
                "best trading strategy",
                "trading strategy recommendation",
                "what strategy should we run",
                "recommend a strategy",
            ],
            "provider_mode": [
                "show provider mode", "what brain are you using", "what brain",
                "use reliable mode", "use gateway mode", "test hermes gateway",
                "disable gateway", "enable gateway", "use local mode",
                "what provider", "provider mode", "which model are you using",
                "what model are you using", "what llm", "which llm",
                "hermes gateway status", "test gateway", "switch to reliable",
                "switch to gateway", "current provider", "current brain",
            ],
            "goals": [
                "what are our goals", "show goals", "what goals do we have",
                "set a goal", "update goal", "goal status",
                "what goal are we working on today", "what are nexus goals",
                "what should nexus work on", "goal registry", "show goal registry",
                "hermes goals", "top goals", "active goals",
            ],
            "tools_scouts": [
                "what tools do you have", "what scouts are available",
                "who should handle this", "assign this to the right scout",
                "what can you do autonomously", "which scout", "scout registry",
                "available scouts", "available tools", "show tools",
                "show scouts", "what agents do you have", "tool registry",
                "what scouts do you have", "scout list",
            ],
            "action_queue": [
                "what are you working on", "show action queue",
                "continue action queue", "what is blocked",
                "what is next", "show completed actions", "action queue",
                "what did you assign", "what actions are open",
                "what did hermes assign", "hermes what are you doing",
                "what is hermes doing",
                "any blockers", "show blockers",
            ],
            "decision_log": [
                "show decision log", "what did you decide",
                "why did you pick that",
                "why did you choose that", "decision log",
                "what did hermes decide", "hermes decisions",
                "show recent decisions", "what did you learn",
                "hermes reasoning",
            ],
            "operating_loop": [
                "run the operating loop", "hermes act as nexus operator",
                "run operating loop", "continue while i am out",
                "continue research while i am out", "hermes run operating loop",
                "operating loop status", "what did the operating loop find",
                "send me a digest", "morning digest", "daily digest",
            ],
            "plain_english": [
                "explain that simply", "give me the plain english version",
                "plain english", "what does that mean", "explain simply",
                "summarize for ceo review", "ceo summary", "in plain language",
                "what does that mean in plain english", "explain in plain language",
            ],
            "technical_details": [
                "show technical details", "show debug details",
                "show logs", "show json", "show file paths", "raw output",
                "technical details", "show debug",
            ],
            "raw_evidence": [
                "show raw evidence", "raw evidence",
                "show artifact paths", "show artifact files",
                "show evidence paths",
            ],
            "daily_intake": [
                "run daily opportunity intake", "run daily intake",
                "what did you find today", "what did nexus find",
                "what sources did you find", "run intake",
                "hermes run daily intake", "collect sources",
                "what sources are pending", "show pending sources",
            ],
            "monetization_actions": [
                "what can make money this week", "show top monetization actions",
                "top monetization actions", "best money moves",
                "what should i monetize", "show monetization opportunities",
                "best opportunities", "top opportunities",
                "what opportunities did you find", "show top actions",
                "top money opportunities",
            ],
            "rejected_opportunities": [
                "show rejected opportunities", "what did you reject",
                "why did you reject", "show rejected sources",
                "rejected list", "what was rejected and why",
                "what was rejected", "show rejected",
            ],
            "scouts_working": [
                "what scouts are working", "scouts working",
                "scout status", "who is assigned",
                "show scout assignments", "scout dispatch status",
                "who is working", "which scouts are dispatched",
            ],
            "daily_review": [
                "show daily research review", "show daily review",
                "daily review", "show research review", "show intake review",
                "what needs review", "show latest review", "show the daily review",
            ],
            "review_first": [
                "what should i review first",
                "what is the next thing i should review",
                "what should i look at first",
                "what needs my review",
            ],
            "build_content_from_opportunity": [
                "build content from the best opportunity",
                "build content from best opportunity",
                "build content from opportunity",
                "create content from top opportunity",
                "write content for best opportunity",
                "build content packet",
                "create draft from best opportunity",
                "create draft from opportunity",
            ],
            "approval_policy": [
                "show approval policy",
                "hermes approval policy",
                "what can you do autonomously",
                "show what hermes can do",
                "what is blocked",
                "what requires my approval",
                "hermes policy",
                "what actions require approval",
                "autonomous policy",
            ],
            "needs_approval": [
                "what needs my approval", "show approval needed",
                "what requires approval", "pending approvals",
                "what needs ray approval",
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


def get_internal_action_config() -> dict[str, bool]:
    """Return internal action mode flags from environment variables."""
    return {
        "internal_action_mode": _env_truthy("HERMES_INTERNAL_ACTION_MODE", "true"),
        "daily_intake_allow_telegram_run": _env_truthy("HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN", "true"),
        "autonomous_internal_actions": _env_truthy("HERMES_AUTONOMOUS_INTERNAL_ACTIONS", "true"),
        "public_actions_require_approval": _env_truthy("HERMES_PUBLIC_ACTIONS_REQUIRE_APPROVAL", "true"),
        "paid_actions_require_approval": _env_truthy("HERMES_PAID_ACTIONS_REQUIRE_APPROVAL", "true"),
        "live_trading_require_approval": _env_truthy("HERMES_LIVE_TRADING_REQUIRE_APPROVAL", "true"),
    }


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
