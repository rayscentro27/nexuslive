"""
hermes_memory_freshness.py
Centralized freshness / staleness rules for Hermes memory sources.
Phase 3B — stale-record safety rules.

Rules defined here:
  - provider_health: active if record <= 15 min old; OFFLINE records > 15 min → needs_review
  - executive_briefings: active if <= 48 hours; older → historical_only
  - conversation_context: active if <= 24 hours; older → stale (do not use for follow-ups)
  - ai_task_queue: active if updated <= 24h and status is queued/running/assigned/pending/in_progress
  - agent_dispatch_tasks: active if updated <= 24h and status is active/pending/running
  - nexus_skills: active if enabled; needs_review if status unknown; historical_only if disabled

No Supabase writes. Classification only.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Literal

# ── Freshness windows ────────────────────────────────────────────────────────

PROVIDER_HEALTH_MAX_AGE_MIN  = 15        # minutes
BRIEFING_MAX_AGE_H           = 48        # hours
CONTEXT_MAX_AGE_H            = 24        # hours
TASK_MAX_AGE_H               = 24        # hours
DISPATCH_MAX_AGE_H           = 24        # hours

# Stale provider values that must never be live answers even if "fresh"
_PROVIDER_STALE_VALUES = frozenset([
    "OFFLINE", "offline", "Ollama OFFLINE", "Beehiiv pending",
    "YouTube Studio pending", "OpenRouter not configured",
])

# Active task statuses
_ACTIVE_TASK_STATUSES = frozenset([
    "queued", "running", "assigned", "pending", "in_progress",
])
_ACTIVE_DISPATCH_STATUSES = frozenset([
    "active", "pending", "running", "assigned", "in_progress",
])
_ACTIVE_SKILL_STATUSES = frozenset(["enabled", "active", "installed"])
_INACTIVE_SKILL_STATUSES = frozenset(["disabled", "deprecated", "removed"])

Classification = Literal[
    "active_live_answer",
    "historical_only",
    "deprecated",
    "blocked_from_live",
    "debug_only",
    "needs_review",
]


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _age_minutes(ts: str | None) -> float | None:
    dt = _parse_ts(ts)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 60


def _age_hours(ts: str | None) -> float | None:
    m = _age_minutes(ts)
    return m / 60 if m is not None else None


# ── Part 1: provider_health ──────────────────────────────────────────────────

def classify_provider_health_record(record: dict) -> Classification:
    """
    Classify a single provider_health row.

    Returns:
      active_live_answer  — fresh (<= 15 min) and not a stale-value OFFLINE claim
      needs_review        — OFFLINE but fresh (could be real; needs live check)
      historical_only     — stale (> 15 min) but not a hard block
      blocked_from_live   — stale OFFLINE/pending claim that must not reach Telegram
    """
    updated_at = record.get("updated_at") or record.get("checked_at") or record.get("timestamp")
    age_min = _age_minutes(updated_at)

    status_val = str(record.get("status", "") or record.get("health", "") or "").strip()
    is_offline_claim = any(s.lower() in status_val.lower() for s in _PROVIDER_STALE_VALUES)

    if age_min is None:
        # No timestamp → cannot verify freshness → needs_review
        return "needs_review"

    if age_min > PROVIDER_HEALTH_MAX_AGE_MIN:
        if is_offline_claim:
            return "blocked_from_live"
        return "historical_only"

    # Fresh (age_min <= 15)
    if is_offline_claim:
        # Fresh OFFLINE: might be real — but still needs_review, not active answer
        return "needs_review"

    return "active_live_answer"


def is_provider_health_fresh(record: dict) -> bool:
    """True if this provider_health record is fresh enough for live answers."""
    return classify_provider_health_record(record) == "active_live_answer"


# ── Part 2: executive_briefings ──────────────────────────────────────────────

def classify_executive_briefing(briefing: dict) -> Classification:
    """
    Classify a single executive_briefings row.

    Returns:
      active_live_answer  — created/updated <= 48 hours ago
      historical_only     — older than 48 hours
    """
    ts = (briefing.get("created_at") or briefing.get("updated_at")
          or briefing.get("generated_at") or briefing.get("timestamp"))
    age_h = _age_hours(ts)

    if age_h is None:
        return "needs_review"

    if age_h > BRIEFING_MAX_AGE_H:
        return "historical_only"

    return "active_live_answer"


def is_briefing_fresh(briefing: dict) -> bool:
    return classify_executive_briefing(briefing) == "active_live_answer"


def briefing_age_hours(briefing: dict) -> float | None:
    ts = (briefing.get("created_at") or briefing.get("updated_at")
          or briefing.get("generated_at") or briefing.get("timestamp"))
    return _age_hours(ts)


# ── Part 3: conversation_context ─────────────────────────────────────────────

def classify_conversation_context(context: dict) -> Classification:
    """
    Classify a hermes_conversation_context.json record.

    Returns:
      active_live_answer  — timestamp <= 24 hours ago
      historical_only     — older than 24 hours (do not use for follow-ups)
    """
    ts = context.get("timestamp")
    age_h = _age_hours(ts)

    if age_h is None:
        return "needs_review"

    if age_h > CONTEXT_MAX_AGE_H:
        return "historical_only"

    return "active_live_answer"


def is_context_fresh(context: dict) -> bool:
    """True if conversation context is fresh enough to resolve follow-up phrases."""
    return classify_conversation_context(context) == "active_live_answer"


def stale_context_clarification() -> str:
    """Return the clarification prompt to use when context is stale."""
    return (
        "Do you mean the latest draft, action, source, or decision? "
        "My session context is older than 24 hours — say 'show it' after "
        "'what do you recommend' to see the latest content draft, "
        "or 'show action queue' for current actions."
    )


# ── Part 4: task / dispatch / skills ─────────────────────────────────────────

def classify_task_record(record: dict, source_table: str = "ai_task_queue") -> Classification:
    """
    Classify a single ai_task_queue or agent_dispatch_tasks row.

    active_live_answer: active status + updated recently
    historical_only:    completed/cancelled/failed, or stale pending
    needs_review:       no timestamp or ambiguous state
    """
    status = str(record.get("status", "") or "").lower().strip()
    ts = record.get("updated_at") or record.get("created_at") or record.get("dispatched_at")
    age_h = _age_hours(ts)

    completed_statuses = frozenset(["completed", "done", "succeeded", "cancelled", "failed", "error"])
    if status in completed_statuses:
        return "historical_only"

    if age_h is None:
        return "needs_review"

    max_age = TASK_MAX_AGE_H if source_table != "agent_dispatch_tasks" else DISPATCH_MAX_AGE_H
    active_statuses = (_ACTIVE_TASK_STATUSES if source_table != "agent_dispatch_tasks"
                       else _ACTIVE_DISPATCH_STATUSES)

    if age_h > max_age:
        # Stale pending/stuck task
        return "historical_only"

    if status in active_statuses:
        return "active_live_answer"

    return "needs_review"


def classify_nexus_skill(skill: dict) -> Classification:
    """
    Classify a single nexus_skills row.

    active_live_answer  — status enabled/active/installed
    needs_review        — status unknown or not in known sets
    historical_only     — status disabled/deprecated/removed
    """
    status = str(skill.get("status", "") or skill.get("enabled", "") or "").lower().strip()

    if status in _ACTIVE_SKILL_STATUSES or status in ("true", "1", "yes"):
        return "active_live_answer"

    if status in _INACTIVE_SKILL_STATUSES or status in ("false", "0", "no"):
        return "historical_only"

    return "needs_review"


# ── Convenience: classify a record from any supported table ──────────────────

def classify_record(table: str, record: dict) -> Classification:
    """Dispatch to the right classifier based on table name."""
    if table == "provider_health":
        return classify_provider_health_record(record)
    if table == "executive_briefings":
        return classify_executive_briefing(record)
    if table == "hermes_conversation_context":
        return classify_conversation_context(record)
    if table in ("ai_task_queue", "agent_dispatch_tasks"):
        return classify_task_record(record, table)
    if table == "nexus_skills":
        return classify_nexus_skill(record)
    return "needs_review"
