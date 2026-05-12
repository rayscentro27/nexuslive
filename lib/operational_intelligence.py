from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import os

from lib import hermes_ops_memory
from lib.hermes_operational_telemetry import build_operational_summary, worker_reliability_rollup


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _safe_select(path: str, timeout: int = 8) -> list[dict[str, Any]]:
    try:
        from scripts.prelaunch_utils import rest_select

        return rest_select(path, timeout=timeout) or []
    except Exception:
        return []


def _queue_pressure(queue_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in queue_rows:
        status = str(row.get("status") or "unknown").lower()
        counts[status] = counts.get(status, 0) + 1
    pending = counts.get("pending", 0) + counts.get("queued", 0) + counts.get("waiting", 0)
    high = pending >= 20
    return {
        "status_counts": counts,
        "pending_count": pending,
        "pressure_level": "high" if high else "normal",
    }


def build_operational_intelligence_snapshot(mode: str = "detailed") -> dict[str, Any]:
    day = datetime.now(timezone.utc).date().isoformat()
    telemetry = build_operational_summary(mode="detailed")
    worker = worker_reliability_rollup(day)
    queue_rows = _safe_select("job_queue?select=id,status,created_at&order=created_at.desc&limit=300")
    queue = _queue_pressure(queue_rows)
    mem = hermes_ops_memory.load_memory(updated_by="operational_intelligence")
    failed_tasks = len(mem.get("recent_failed") or [])
    completed_tasks = len(mem.get("recent_completed") or [])
    pending_approvals = len(mem.get("pending_approval_refs") or [])
    degraded = list(worker.get("degraded_worker_warnings") or [])
    if queue.get("pressure_level") == "high":
        degraded.append("Queue pressure is elevated; prioritize pending approvals and blocked items.")
    risk_level = "low"
    if degraded or failed_tasks >= 5:
        risk_level = "medium"
    if len(degraded) >= 3 or failed_tasks >= 10:
        risk_level = "high"
    next_action = "Maintain current operational rhythm and monitor reliability trends."
    if pending_approvals > 0:
        next_action = "Review and clear pending approvals to reduce queue latency."
    elif queue.get("pressure_level") == "high":
        next_action = "Reduce queue pressure by resolving stalled and pending jobs."
    elif degraded:
        next_action = "Investigate degraded components and apply manual cooldown/retry checks."
    detailed = {
        "timestamp": _now(),
        "enabled": _flag("OPERATIONAL_INTELLIGENCE_ENABLED", "true"),
        "system_health": {
            "safety_posture": telemetry.get("safety") or {},
            "risk_level": risk_level,
        },
        "worker_health": worker,
        "queue_pressure": queue,
        "failed_tasks": failed_tasks,
        "completed_tasks": completed_tasks,
        "pending_approvals": pending_approvals,
        "degraded_components": degraded,
        "recommended_next_action": next_action,
        "risk_level": risk_level,
        "executive_summary": (
            f"Risk {risk_level.upper()} with {queue.get('pending_count', 0)} pending queue items, "
            f"{failed_tasks} recent failures, and {pending_approvals} pending approvals."
        ),
        "telegram_reliability": telemetry.get("telegram_reliability") or {},
        "operational_telemetry": telemetry,
    }
    if str(mode).lower() == "compact":
        return {
            "timestamp": detailed["timestamp"],
            "enabled": detailed["enabled"],
            "risk_level": detailed["risk_level"],
            "worker_health": {
                "failure_count": int((worker.get("failure_count") or 0)),
                "stale_worker_heartbeats": int((worker.get("stale_worker_heartbeats") or 0)),
            },
            "queue_pressure": {
                "pending_count": int((queue.get("pending_count") or 0)),
                "pressure_level": queue.get("pressure_level") or "normal",
            },
            "recommended_next_action": detailed["recommended_next_action"],
            "executive_summary": detailed["executive_summary"],
        }
    return detailed
