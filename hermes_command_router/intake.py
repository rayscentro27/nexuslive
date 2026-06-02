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
      "need my sign", "approval required",
      "needs approval", "what is pending my"],                      "handoff_check",             "high",   False),

    (["what evidence do you have", "show verified status",
      "show me verified", "verified status only",
      "what is verified", "show evidence",
      "evidence only", "what artifacts do you have"],               "nexus_status",              "high",   False),

    (["what youtube videos did i send", "what youtube did i send today",
      "youtube videos today", "which youtube did i send",
      "what links did i send today", "what videos did i send"],     "source_intake_status",      "medium", False),

    (["what happened to the last link", "last link i sent",
      "what did you do with the link", "did you process the link",
      "what happened to the link i sent"],                          "source_intake_status",      "medium", False),

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

    # ── Knowledge gap review commands (before generic research entry) ──────────
    (["show knowledge gaps", "show unanswered questions",
      "what could you not answer", "show gaps",
      "what questions were unanswered", "show unanswered",
      "what did you not know", "what gaps do you have",
      "hermes show knowledge gaps"],                                   "knowledge_gap_review",        "low",    False),

    (["research unanswered", "create better answers for gaps",
      "research knowledge gaps", "improve gap answers",
      "fix knowledge gaps", "resolve knowledge gaps",
      "create gap research tasks", "improve hermes answers",
      "unanswered questions research"],                               "knowledge_gap_research",      "low",    True),

    (["archive resolved gaps", "clear resolved gaps",
      "archive old gaps", "mark gaps resolved"],                      "knowledge_gap_archive",       "low",    True),

    # "fastest" contains substring "test" — must be before run_tests entry
    (["fastest money", "fastest revenue", "fastest path to money",
      "fastest money path"],                                       "business_opportunities",    "medium", False),

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
      "funding broker", "opportunities ready",
      # monetization natural language phrases
      "how do we make money", "how can we make money",
      "how to make money today", "best money making opportunity",
      "what can make money", "money making opportunity",
      "best revenue move", "next best money move",
      "what should we monetize", "make money right now",
      # monetization audit and plan commands
      "nexus monetization audit", "run nexus monetization audit",
      "show monetization audit", "monetization audit",
      "monetization plan", "monetization priorities",
      "revenue plan for today", "fastest money path",
      "what is our fastest money path"],                            "business_opportunities",    "medium", False),
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

    # ── Active operating rules (must be BEFORE memory sources and research catches) ──
    (["show active operating rules", "active operating rules",
      "what active rules are you using", "what rules are you following",
      "show hermes rules", "show live answer rules", "show approval rules",
      "what approval rules are active"],                               "active_operating_rules",     "low",    False),

    # ── Memory sources / debug commands (must be BEFORE archived_executive_memory) ──
    (["show memory sources", "memory sources", "what memory sources",
      "what are your memory sources", "where does your memory come from",
      "where do you get memory from", "what memory do you use",
      "what sources do you use", "show your memory sources"],         "memory_sources",             "low",    False),

    # ── Archived (stale) executive memory commands ──────────────────────────
    (["archived memory", "stale defaults", "load archived defaults",
      "show archived defaults", "archived executive memory",
      "what were the old defaults", "original defaults",
      "what was in the old executive memory",
      "show old executive memory", "show historical executive memory",
      "old executive memory", "historical executive memory"],        "archived_executive_memory", "low",    False),

    (["where did that answer come from", "where does that come from",
      "where does your answer come from", "cite that answer",
      "cite source", "answer source", "what source did you use",
      "why did you answer that"],                   "answer_source",               "low",    False),

    (["show stale memory debug", "stale memory debug", "stale debug",
      "debug memory", "show debug memory",
      "show blocked memory debug", "show deprecated memory debug",
      "blocked memory debug", "deprecated memory debug"],            "stale_memory_debug",        "low",    False),

    # ── Provider / brain status ──────────────────────────────────────────────
    (["what brain are you using", "which brain",
      "are you using chatgpt", "chatgpt auth", "are you using openai",
      "are you using openrouter", "is openrouter enabled", "openrouter status",
      "show provider status", "provider status", "which llm", "what llm",
      "what model are you using", "which model", "brain status",
      "disable openrouter", "disable open router",
      "show evidence mode status", "evidence mode status",
      "what provider", "which provider"],                          "provider_status",             "low",    False),

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
