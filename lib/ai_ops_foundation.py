"""
ai_ops_foundation.py — Non-destructive AI operations telemetry foundation.

This module provides lightweight tracking helpers without schema changes.
Events are written to `hermes_aggregates` using namespaced event_source values.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _post_aggregate(event_source: str, event_type: str, summary: str, alert_sent: bool = False) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    body = {
        "event_source": event_source,
        "event_type": event_type,
        "classification": "ops_metric",
        "aggregated_summary": summary[:500],
        "alert_sent": alert_sent,
    }
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/hermes_aggregates",
            data=json.dumps(body).encode(),
            headers=_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8):
            return True
    except Exception:
        return False


def track_model_usage(task_type: str, provider: str, model: str, duration_ms: int, ok: bool) -> bool:
    stamp = datetime.now(timezone.utc).isoformat()
    summary = (
        f"ts={stamp} task={task_type} provider={provider} model={model} "
        f"duration_ms={duration_ms} ok={ok}"
    )
    return _post_aggregate("ai_ops_model_usage", "model_usage", summary)


def track_retry_event(component: str, error_class: str, attempt: int, max_attempts: int) -> bool:
    stamp = datetime.now(timezone.utc).isoformat()
    summary = (
        f"ts={stamp} component={component} error={error_class} attempt={attempt}/{max_attempts}"
    )
    return _post_aggregate("ai_ops_retries", "retry_event", summary)


def track_worker_health(worker_id: str, status: str, detail: str = "") -> bool:
    stamp = datetime.now(timezone.utc).isoformat()
    summary = f"ts={stamp} worker={worker_id} status={status} detail={detail}".strip()
    return _post_aggregate("ai_ops_worker_health", "worker_health", summary)
