"""
intake.py — Normalize inbound messages from any source into a unified command object.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Literal

Source  = Literal["email", "telegram", "cli"]
Priority = Literal["critical", "high", "medium", "low"]


def normalize(
    raw_text: str,
    source: Source = "cli",
    sender: str = "raymond",
    message_id: str = "",
    reply_channel: str = "",
) -> dict:
    """Return a normalized command object."""
    now = datetime.now(timezone.utc).isoformat()
    mid = message_id or f"cmd-{uuid.uuid4().hex[:12]}"
    dedupe_key = hashlib.sha256(f"{source}:{sender}:{raw_text[:200]}".encode()).hexdigest()[:32]

    intent, priority, requires_approval = classify_intent(raw_text)

    return {
        "command_id":              mid,
        "source":                  source,
        "raw_text":                raw_text,
        "sender":                  sender,
        "received_at":             now,
        "message_id":              mid,
        "dedupe_key":              dedupe_key,
        "intent":                  intent,
        "priority":                priority,
        "status":                  "pending",
        "reply_channel":           reply_channel or source,
        "requires_human_approval": requires_approval,
    }


# Deterministic intent classification — no AI needed for common commands.
# IMPORTANT: higher-priority special phrases are checked first.
_INTENT_MAP: list[tuple[list[str], str, Priority, bool]] = [
    # (keywords, intent, priority, requires_approval)

    # ── Dev Agent Bridge (must appear BEFORE generic keyword catches) ───────────
    (["list dev agents", "which coding agents", "coding agents available",
      "what agents", "dev agents", "available agents", "agent bridge",
      "run dev agent status"],                                "list_dev_agents",           "low",    False),

    (["ask gemini", "prepare a prompt for gemini",
      "use gemini", "gemini review", "gemini analyze",
      "ask opencode", "prepare a prompt for opencode",
      "use opencode", "opencode implement",
      "ask claude cli", "prepare a prompt for claude",
      "claude cli review",
      "ask codex", "prepare a prompt for codex",
      "use codex", "codex patch"],                            "prepare_dev_handoff",       "medium", True),

    (["recommend agent", "which agent should", "what agent should",
      "best agent for", "which cli agent", "suggest agent",
      "which coding agent"],                                  "recommend_dev_agent",       "low",    False),

    # ── Special phrases (must be before generic keyword catches) ────────────────
    (["are we ready", "ready for pilot", "10-user pilot", "10 user pilot",
      "pilot ready", "pilot launch", "ready to launch", "ready for launch"],
                                                           "pilot_readiness",           "high",   False),

    (["next best move", "what should we do", "what's the next",
      "what is the next step", "what do you recommend", "recommend",
      "best move", "next move", "what now"],               "next_best_move",            "high",   False),

    # ── Strategic operating partner (must be BEFORE generic keyword catches) ────
    (["catch me up", "where are we", "are we on track",
      "what did nexus produce", "what happened since",
      "nexus status", "what's the nexus status"],                   "nexus_status",              "high",   False),

    (["pending handoff", "what needs my approval",
      "waiting on me", "show handoffs", "what do you need",
      "need my sign", "approval required"],                         "handoff_check",             "high",   False),

    (["hermes decided", "decision log", "what did hermes decide",
      "autonomous decision", "hermes own decision"],                "decision_log",              "medium", False),

    (["demo order", "oanda demo", "demo broker",
      "demo trade", "last trade demo", "practice order"],           "demo_broker_status",        "medium", False),

    (["beehiiv", "beehive", "bee hive", "bee-hive", "behive", "behiiv",
      "newsletter alternative", "newsletter platform",
      "email platform alternative", "newsletter tool alternative",
      "premium blocker",
      "free alternative", "replace beehiiv",
      "cheap alternative", "tool blocker"],                         "premium_blocker_resolver",  "low",    False),

    (["record lesson", "remember this", "save feedback",
      "save lesson", "note this", "log lesson"],                    "save_ray_feedback",         "low",    False),

    (["notification log", "telegram notification",
      "what did hermes send", "hermes notification",
      "notification sent", "proactive notification"],               "notification_log",          "low",    False),

    (["can you hear me", "test communication", "hello hermes",
      "are you there", "is this working", "comm check", "comms check",
      "communication test", "ping"],                       "communication_health",      "medium", False),

    # ── Standard commands ───────────────────────────────────────────────────────
    (["health", "backend", "system check", "check system"],      "health_check",              "medium", False),
    (["worker", "heartbeat", "workers"],                          "worker_status",             "medium", False),
    (["queue", "backlog", "pending signal"],                       "queue_status",              "medium", False),
    (["test", "run test"],                                         "run_tests",                 "medium", False),
    (["trading", "trade", "position", "oanda"],                    "trading_lab_status",        "high",   False),
    (["funding", "fund"],                                          "funding_status",            "medium", False),
    (["credit", "score", "fico"],                                  "credit_workflow_status",    "medium", False),
    (["grant", "grants"],                                          "grant_research_status",     "low",    False),
    (["research", "youtube", "signal"],                            "research_task",             "low",    False),
    # ── CEO digest / anomaly — must come before generic "ceo" keyword ────────
    (["ceo digest", "ceo report", "ceo brief", "executive digest",
      "daily digest", "show me the digest", "platform digest",
      "anomaly", "anomalies", "what's broken", "what is broken",
      "health report", "platform health"],                         "ceo_digest",                "high",   False),
    (["ceo", "daily report", "weekly report", "brief"],            "summarize_recent_activity", "high",   False),
    (["refactor", "fix", "build", "implement", "code", "write"],   "code_task",                 "high",   True),
    (["deploy", "push", "release", "rm ", "delete ", "drop "],     "code_task",                 "critical", True),
    (["summary", "summarize", "activity"],                         "summarize_recent_activity", "medium", False),

    # ── Nexus intelligence intents ───────────────────────────────────────────────
    (["business opportunity", "business opportunities", "what opportunities",
      "show opportunities", "best opportunity", "top opportunity",
      "side hustle", "ai content agency", "credit repair consulting",
      "funding broker", "opportunities ready"],                     "business_opportunities",    "medium", False),
    (["app url", "website url", "what is the url", "what's the url",
      "app link", "platform url", "nexus url", "goclear",
      "what is the app", "where is the app", "how do i access"],   "app_url",                   "low",    False),
    (["onboarding", "getting started", "setup steps", "new user",
      "how to start", "first steps"],                              "onboarding_status",         "medium", False),
    (["user intelligence", "user score", "engagement score",
      "user profile", "user readiness", "who are my users"],       "user_intelligence_status",  "medium", False),
    (["platform analytics", "usage stats",
      "how many users", "user count", "active users"],             "platform_analytics",        "medium", False),
    # ── Source intake status queries ─────────────────────────────────────────
    (["show source intake", "what links did i send", "what youtube did i send",
      "what happened to the last link", "show failed source", "continue processing",
      "reroute this source", "assign this to claude", "assign to youtube",
      "show pending source", "source intake queue",
      "what artifacts did nexus create", "what did claude code finish",
      "what did codex finish", "show unregistered artifacts",
      "backfill the artifact registry"],                           "source_intake_status",       "medium", False),
    (["show artifact registry", "artifact registry", "show all artifacts",
      "what artifacts exist"],                                     "artifact_registry_status",   "low",    False),
]


def classify_intent(text: str) -> tuple[str, Priority, bool]:
    import re as _re
    # Detect any URL → source intake
    if _re.search(r'https?://[^\s]+', text):
        return "source_intake", "medium", False
    lowered = text.lower()
    for keywords, intent, priority, requires_approval in _INTENT_MAP:
        if any(kw in lowered for kw in keywords):
            return intent, priority, requires_approval
    return "unknown", "medium", False
