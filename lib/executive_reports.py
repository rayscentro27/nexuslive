from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from lib import hermes_ops_memory
from lib.hermes_knowledge_brain import knowledge_dashboard_snapshot
from lib.agent_collaboration import dry_run_collaboration_plan


def _safe_select(path: str, timeout: int = 8) -> list[dict[str, Any]]:
    try:
        from scripts.prelaunch_utils import rest_select

        return rest_select(path, timeout=timeout) or []
    except Exception:
        return []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_ai_workforce_summary() -> dict[str, Any]:
    mem = hermes_ops_memory.load_memory(updated_by="executive_reports_workforce")
    worker_rows = _safe_select("worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=40")
    worker_status: dict[str, int] = {}
    for row in worker_rows:
        key = str(row.get("status") or "unknown").lower()
        worker_status[key] = worker_status.get(key, 0) + 1
    queue_rows = _safe_select("job_queue?select=id,status,created_at&order=created_at.desc&limit=80")
    queue_status: dict[str, int] = {}
    for row in queue_rows:
        key = str(row.get("status") or "unknown").lower()
        queue_status[key] = queue_status.get(key, 0) + 1
    recent_events = _safe_select("system_events?select=id,event_type,status,created_at&order=created_at.desc&limit=80")
    telegram_events = [
        row for row in recent_events if "telegram" in str(row.get("event_type") or "").lower()
    ]
    return {
        "timestamp": _now(),
        "latest_agent_runs": mem.get("latest_agent_runs") or {},
        "task_lifecycle_summary": mem.get("task_lifecycle_summary") or {},
        "recent_failures": mem.get("recent_failed") or [],
        "pending_approvals": mem.get("pending_approval_refs") or [],
        "worker_status_summary": worker_status,
        "job_queue_status_summary": queue_status,
        "recent_telegram_activity": {
            "event_count": len(telegram_events),
            "latest": telegram_events[:8],
        },
    }


def build_knowledge_brain_report() -> dict[str, Any]:
    snap = knowledge_dashboard_snapshot()
    return {
        "timestamp": _now(),
        "category_counts": snap.get("category_counts") or {},
        "stale_warnings": snap.get("stale_warnings") or [],
        "source_quality_summary": snap.get("source_quality_summary") or {},
        "top_ranked_knowledge": snap.get("top_ranked_knowledge") or {},
        "funding_insights": snap.get("recent_funding_insights") or [],
        "credit_insights": snap.get("recent_credit_insights") or [],
    }


def build_executive_report() -> dict[str, Any]:
    mem = hermes_ops_memory.load_memory(updated_by="executive_reports_daily")
    knowledge = build_knowledge_brain_report()
    collaboration = dry_run_collaboration_plan("daily operational intelligence")
    workforce = build_ai_workforce_summary()
    recent_failures = workforce.get("recent_failures") or []
    if not recent_failures:
        recent_failures = [
            {
                "task": "none",
                "reason": "No recent failures recorded.",
            }
        ]
    next_actions = [
        "Review pending approvals and clear blockers.",
        "Investigate any failed tasks and assign owner follow-up.",
        "Prioritize top ranked funding and credit recommendations.",
    ]
    return {
        "report_type": "daily_executive_summary",
        "timestamp": _now(),
        "operational_memory": {
            "active_work_session": hermes_ops_memory.get_active_work_session(mem),
            "recent_recommendations": mem.get("recent_recommendations") or [],
            "recent_completed": mem.get("recent_completed") or [],
            "recent_failed": mem.get("recent_failed") or [],
            "pending_approval_refs": mem.get("pending_approval_refs") or [],
        },
        "knowledge": knowledge,
        "workforce": workforce,
        "system_health": {
            "worker_status_summary": workforce.get("worker_status_summary") or {},
            "job_queue_status_summary": workforce.get("job_queue_status_summary") or {},
        },
        "recent_failures": recent_failures[:10],
        "telegram_activity": workforce.get("recent_telegram_activity") or {},
        "next_recommended_actions": next_actions,
        "collaboration_preview": collaboration,
        "funding_credit_summary": {
            "funding": knowledge.get("funding_insights") or [],
            "credit": knowledge.get("credit_insights") or [],
        },
    }


def build_weekly_ceo_report() -> dict[str, Any]:
    daily = build_executive_report()
    daily["report_type"] = "weekly_ceo_report"
    daily["weekly_focus"] = "Consolidate operational wins, blockers, and ranked knowledge signals."
    return daily


def _as_text(payload: dict[str, Any]) -> str:
    lines = [
        f"Report Type: {payload.get('report_type', 'executive')}",
        f"Timestamp: {payload.get('timestamp')}",
        "",
        "Operational Memory:",
        str(payload.get("operational_memory") or {}),
        "",
        "Knowledge Summary:",
        str((payload.get("knowledge") or {}).get("category_counts") or {}),
        f"Stale warnings: {len((payload.get('knowledge') or {}).get('stale_warnings') or [])}",
        "",
        "Funding Insights:",
        str((payload.get("funding_credit_summary") or {}).get("funding") or []),
        "",
        "Credit Insights:",
        str((payload.get("funding_credit_summary") or {}).get("credit") or []),
    ]
    return "\n".join(lines)


def send_executive_report_email(send_report_email: Callable[[str, str], Any], report_type: str = "daily") -> dict[str, Any]:
    payload = build_weekly_ceo_report() if report_type == "weekly" else build_executive_report()
    subject_prefix = "Nexus Weekly CEO Report" if report_type == "weekly" else "Nexus Executive Report"
    subject = f"{subject_prefix} - {_now()}"
    body = _as_text(payload)
    result = send_report_email(subject, body)
    out = {
        "subject": subject,
        "report": payload,
        "email": result if isinstance(result, dict) else {"sent": bool(result), "configured": bool(result), "error": ""},
    }
    try:
        from lib.event_intake import submit_system_event

        submit_system_event(
            "executive_report_generated",
            status="completed" if (out.get("email") or {}).get("sent") else "partial",
            payload={
                "report_type": report_type,
                "subject": subject,
                "email": out.get("email") or {},
                "timestamp": payload.get("timestamp"),
            },
        )
    except Exception:
        pass
    return out
