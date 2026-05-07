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

    # ── Special phrases (must be before generic keyword catches) ────────────────
    (["are we ready", "ready for pilot", "10-user pilot", "10 user pilot",
      "pilot ready", "pilot launch", "ready to launch", "ready for launch"],
                                                           "pilot_readiness",           "high",   False),

    (["next best move", "what should we do", "what's the next",
      "what is the next step", "what do you recommend", "recommend",
      "best move", "next move", "what now"],               "next_best_move",            "high",   False),

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
    (["ceo", "daily report", "weekly report", "brief"],            "summarize_recent_activity", "high",   False),
    (["refactor", "fix", "build", "implement", "code", "write"],   "code_task",                 "high",   True),
    (["deploy", "push", "release", "rm ", "delete ", "drop "],     "code_task",                 "critical", True),
    (["summary", "summarize", "activity"],                         "summarize_recent_activity", "medium", False),
]


def classify_intent(text: str) -> tuple[str, Priority, bool]:
    lowered = text.lower()
    for keywords, intent, priority, requires_approval in _INTENT_MAP:
        if any(kw in lowered for kw in keywords):
            return intent, priority, requires_approval
    return "unknown", "medium", False
