"""
notification_policy.py — Severity classification and digest rules for Hermes notifications.

Usage:
    from lib.notification_policy import classify_event, SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_CRITICAL

    severity = classify_event("worker_crash", data={"failures": 3})
    # returns SEVERITY_CRITICAL
"""
from __future__ import annotations

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"
SEVERITY_SUMMARY = "summary"
SEVERITY_RECOVERY = "recovery"

# Events that are CRITICAL — immediate Telegram alert
CRITICAL_EVENTS: frozenset[str] = frozenset({
    "worker_crash",
    "orchestrator_failure",
    "backend_offline",
    "api_offline",
    "payment_failure",
    "queue_stuck",
    "failed_automation",
    "security_issue",
    "auth_issue",
    "repeated_model_failure",
    "repeated_api_failure",
})

# Events that are WARNING — include in daily digest, immediate if repeated/escalated
WARNING_EVENTS: frozenset[str] = frozenset({
    "worker_unhealthy",
    "model_degraded",
    "api_rate_limited",
    "queue_backlog",
    "scheduler_delayed",
    "signal_stale",
    "broker_disconnected",
    "high_error_rate",
})

# Events that are INFO — log only / include in daily digest
INFO_EVENTS: frozenset[str] = frozenset({
    "routine_complete",
    "job_success",
    "queue_moved",
    "info_log",
    "workflow_complete",
    "model_call",
    "health_check_ok",
})

# Events that are SUMMARY — daily digest only
SUMMARY_EVENTS: frozenset[str] = frozenset({
    "daily_digest",
    "lead_summary",
    "reputation_summary",
    "funding_brief",
    "research_digest",
    "ops_summary",
})

# Events that are RECOVERY — sent when a previously failing system recovers
RECOVERY_EVENTS: frozenset[str] = frozenset({
    "worker_recovered",
    "backend_online",
    "api_online",
    "queue_cleared",
    "broker_reconnected",
})


def classify_event(event_type: str, data: dict | None = None) -> str:
    """Classify an event type into a severity level."""
    normalized = event_type.strip().lower().replace(" ", "_")

    if normalized in CRITICAL_EVENTS:
        return SEVERITY_CRITICAL
    if normalized in WARNING_EVENTS:
        return SEVERITY_WARNING
    if normalized in RECOVERY_EVENTS:
        return SEVERITY_RECOVERY
    if normalized in SUMMARY_EVENTS:
        return SEVERITY_SUMMARY
    if normalized in INFO_EVENTS:
        return SEVERITY_INFO

    # Default heuristic for unknown events
    if data:
        failures = data.get("failures") or data.get("consecutive_failures", 0)
        if failures and failures >= 3:
            return SEVERITY_CRITICAL
        if failures and failures >= 1:
            return SEVERITY_WARNING

    return SEVERITY_INFO


def should_alert_immediately(severity: str) -> bool:
    """Return True if this severity triggers an immediate Telegram alert."""
    return severity in {SEVERITY_CRITICAL, SEVERITY_RECOVERY}


def should_include_in_digest(severity: str) -> bool:
    """Return True if this severity should appear in the daily digest."""
    return severity in {SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_CRITICAL, SEVERITY_SUMMARY}
