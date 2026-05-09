from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from lib import hermes_ops_memory
from lib.hermes_knowledge_brain import knowledge_dashboard_snapshot
from lib.agent_collaboration import dry_run_collaboration_plan


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_ai_workforce_summary() -> dict[str, Any]:
    mem = hermes_ops_memory.load_memory(updated_by="executive_reports_workforce")
    return {
        "timestamp": _now(),
        "latest_agent_runs": mem.get("latest_agent_runs") or {},
        "task_lifecycle_summary": mem.get("task_lifecycle_summary") or {},
        "recent_failures": mem.get("recent_failed") or [],
        "pending_approvals": mem.get("pending_approval_refs") or [],
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
        "workforce": build_ai_workforce_summary(),
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
    return out
