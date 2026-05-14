from __future__ import annotations

import os


ALLOWED_EVENT_TYPES = {
    "conversational_reply",
    "critical_alert",
    "explicit_operator_requested_digest",
    "coding_agent_completion_ack",
}

BLOCKED_EVENT_TYPES = {
    "research_summary",
    "ingestion_summary",
    "queue_summary",
    "scheduler_summary",
    "worker_summary",
    "ticket_summary",
    "provider_summary",
    "auto_digest",
    "full_report",
}


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def should_send_telegram_notification(
    event_type: str | None,
    *,
    user_requested: bool = False,
    conversational: bool = False,
    critical: bool = False,
) -> tuple[bool, str]:
    et = (event_type or "").strip().lower()
    if not et:
        return False, "missing_event_type"

    if et in BLOCKED_EVENT_TYPES:
        return False, "blocked_event_type"

    if conversational and et == "conversational_reply":
        return True, "allowed_conversational"

    if critical and et == "critical_alert":
        return (_flag("TELEGRAM_CRITICAL_ALERTS_ENABLED", "true"), "critical_gate")

    if user_requested and et == "explicit_operator_requested_digest":
        return True, "allowed_user_requested_digest"

    if et == "coding_agent_completion_ack" and user_requested:
        return True, "allowed_coding_ack"

    operational_enabled = _flag("TELEGRAM_OPERATIONAL_NOTIFICATIONS_ENABLED", "false")
    if not operational_enabled:
        return False, "operational_notifications_disabled"

    if et not in ALLOWED_EVENT_TYPES:
        return False, "default_deny_not_allowlisted"
    return True, "allowlisted"
