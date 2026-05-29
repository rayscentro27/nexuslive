"""
hermes_notification_policy.py
================================
Anti-spam notification policy for the Daily Opportunity Intake cycle.

Ray does NOT want Telegram spam. Hermes should quietly collect, process,
score, and assign work — then send ONE concise digest when ready.

Rules:
  - suppress: source_registered, source_rejected, scout_assigned, artifact_created, opportunity_scored
  - allow:    approval_required, blocker, high_value_opportunity, digest_ready, cycle_complete
  - max 1 digest per cycle by default
  - batch similar events together

Config env vars (all default to the safe/quiet side):
  HERMES_TELEGRAM_DIGEST_MODE              (default: true)
  HERMES_TELEGRAM_MAX_DIGESTS_PER_DAY      (default: 3)
  HERMES_TELEGRAM_NOTIFY_ON_EACH_SOURCE    (default: false)
  HERMES_TELEGRAM_NOTIFY_ON_REJECTED_SOURCE(default: false)
  HERMES_TELEGRAM_NOTIFY_ON_SCOUT_ASSIGNMENT(default: false)
  HERMES_TELEGRAM_NOTIFY_ON_ARTIFACT_CREATED(default: false)
  HERMES_TELEGRAM_NOTIFY_ON_APPROVAL_REQUIRED(default: true)
  HERMES_TELEGRAM_NOTIFY_ON_BLOCKER        (default: true)
  HERMES_TELEGRAM_NOTIFY_ON_HIGH_VALUE_OPPORTUNITY(default: true)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ── Config ────────────────────────────────────────────────────────────────────

def _bool_env(key: str, default: bool) -> bool:
    val = os.getenv(key, "").strip().lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default

DIGEST_MODE             = _bool_env("HERMES_TELEGRAM_DIGEST_MODE", True)
MAX_DIGESTS_PER_DAY     = int(os.getenv("HERMES_TELEGRAM_MAX_DIGESTS_PER_DAY", "3"))
NOTIFY_EACH_SOURCE      = _bool_env("HERMES_TELEGRAM_NOTIFY_ON_EACH_SOURCE", False)
NOTIFY_REJECTED_SOURCE  = _bool_env("HERMES_TELEGRAM_NOTIFY_ON_REJECTED_SOURCE", False)
NOTIFY_SCOUT_ASSIGNMENT = _bool_env("HERMES_TELEGRAM_NOTIFY_ON_SCOUT_ASSIGNMENT", False)
NOTIFY_ARTIFACT_CREATED = _bool_env("HERMES_TELEGRAM_NOTIFY_ON_ARTIFACT_CREATED", False)
NOTIFY_APPROVAL_REQUIRED= _bool_env("HERMES_TELEGRAM_NOTIFY_ON_APPROVAL_REQUIRED", True)
NOTIFY_BLOCKER          = _bool_env("HERMES_TELEGRAM_NOTIFY_ON_BLOCKER", True)
NOTIFY_HIGH_VALUE       = _bool_env("HERMES_TELEGRAM_NOTIFY_ON_HIGH_VALUE_OPPORTUNITY", True)

# ── Event type definitions ────────────────────────────────────────────────────

ALL_EVENT_TYPES = frozenset({
    "source_registered",
    "source_rejected",
    "scout_assigned",
    "artifact_created",
    "opportunity_scored",
    "high_value_opportunity",
    "blocker",
    "approval_required",
    "digest_ready",
    "cycle_complete",
})

# ── Core policy functions ─────────────────────────────────────────────────────

def should_notify_ray(
    event_type: str,
    priority: str = "normal",
    context: dict[str, Any] | None = None,
) -> bool:
    """Return True if this event should send a Telegram message to Ray."""
    context = context or {}

    if event_type == "source_registered":
        return NOTIFY_EACH_SOURCE
    if event_type == "source_rejected":
        return NOTIFY_REJECTED_SOURCE
    if event_type == "scout_assigned":
        return NOTIFY_SCOUT_ASSIGNMENT
    if event_type == "artifact_created":
        return NOTIFY_ARTIFACT_CREATED
    if event_type == "opportunity_scored":
        score = context.get("monetization_score", 0)
        return NOTIFY_HIGH_VALUE and int(score) >= 75
    if event_type == "high_value_opportunity":
        return NOTIFY_HIGH_VALUE
    if event_type == "blocker":
        return NOTIFY_BLOCKER
    if event_type == "approval_required":
        return NOTIFY_APPROVAL_REQUIRED
    if event_type in ("digest_ready", "cycle_complete"):
        return True
    return False


def suppress_low_value_notifications(events: list[dict]) -> list[dict]:
    """Filter event list to only those that should notify Ray."""
    return [e for e in events if should_notify_ray(
        e.get("event_type", ""),
        e.get("priority", "normal"),
        e.get("context", {}),
    )]


def batch_notifications(events: list[dict]) -> list[dict]:
    """
    Group similar suppressed events into batches.
    Returns a reduced list: one entry per event_type that passes policy.
    Events that don't pass policy are dropped silently.
    """
    passed = suppress_low_value_notifications(events)
    # Deduplicate: for non-urgent events, keep only the most important one per type
    seen: dict[str, dict] = {}
    urgent = []
    for e in passed:
        et = e.get("event_type", "")
        if et in ("approval_required", "blocker"):
            urgent.append(e)
        elif et not in seen:
            seen[et] = e
    return urgent + list(seen.values())


def create_digest_notification(cycle_results: dict) -> str:
    """Build a concise plain-language Telegram digest from cycle results."""
    total       = cycle_results.get("total_sources", 0)
    useful      = cycle_results.get("useful_sources", 0)
    rejected    = cycle_results.get("rejected_sources", 0)
    top_rec     = cycle_results.get("top_recommendation", "")
    needs_approval = cycle_results.get("needs_approval", [])
    blockers    = cycle_results.get("blockers", [])
    top_ops     = cycle_results.get("top_opportunities", [])
    artifact    = cycle_results.get("intake_artifact_path", "")
    decision_artifact = cycle_results.get("decision_artifact_path", "")

    lines = [
        "📊 **Hermes Daily Digest**",
        "",
        f"I reviewed {total} sources. {useful} look useful. {rejected} were rejected.",
    ]

    if top_rec:
        lines.append(f"Best move: {top_rec}")

    if top_ops:
        lines.append("")
        lines.append("**Top opportunities:**")
        for i, op in enumerate(top_ops[:3], 1):
            title = op.get("title", op.get("source_title", ""))
            score = op.get("monetization_score", 0)
            lines.append(f"  {i}. {title} (score: {score})")

    if needs_approval:
        lines.append("")
        lines.append("**Needs your approval:**")
        for item in needs_approval[:3]:
            lines.append(f"  ⏳ {item}")

    if blockers:
        lines.append("")
        lines.append("**Blockers:**")
        for b in blockers[:2]:
            lines.append(f"  🔴 {b}")

    if artifact:
        lines.append("")
        lines.append(f"Evidence: {artifact}")

    lines += [
        "",
        "Reply: `show top actions` | `show rejected` | `approve <id>` | `build content packet`",
    ]

    return "\n".join(lines)


def create_approval_notification(item: dict) -> str:
    """Build a plain-language approval request message."""
    title  = item.get("title", "item")
    reason = item.get("approval_reason", "requires Ray approval")
    cost   = item.get("cost", "")
    cost_line = f" (cost: {cost})" if cost else ""
    return (
        f"⏳ **Approval needed:** {title}{cost_line}\n"
        f"Reason: {reason}\n"
        "Reply: `approve` | `reject` | `details`"
    )


def create_blocker_notification(blocker: dict) -> str:
    """Build a plain-language blocker alert."""
    title   = blocker.get("title", "blocker")
    details = blocker.get("details", "")
    fix     = blocker.get("recommended_fix", "")
    lines = [f"🔴 **Blocker:** {title}"]
    if details:
        lines.append(details)
    if fix:
        lines.append(f"Recommended fix: {fix}")
    return "\n".join(lines)


def notification_policy_summary() -> str:
    """Return a plain-language summary of current notification policy."""
    lines = [
        "Hermes notification policy (anti-spam):",
        f"  Digest mode: {'on' if DIGEST_MODE else 'off'}",
        f"  Max digests/day: {MAX_DIGESTS_PER_DAY}",
        f"  Notify on each source: {NOTIFY_EACH_SOURCE}",
        f"  Notify on rejected source: {NOTIFY_REJECTED_SOURCE}",
        f"  Notify on scout assignment: {NOTIFY_SCOUT_ASSIGNMENT}",
        f"  Notify on artifact created: {NOTIFY_ARTIFACT_CREATED}",
        f"  Notify on approval required: {NOTIFY_APPROVAL_REQUIRED}",
        f"  Notify on blocker: {NOTIFY_BLOCKER}",
        f"  Notify on high-value opportunity: {NOTIFY_HIGH_VALUE}",
    ]
    return "\n".join(lines)
