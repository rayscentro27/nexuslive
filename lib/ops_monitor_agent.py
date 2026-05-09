from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

from lib import hermes_ops_memory
from lib.hermes_knowledge_brain import get_recent_recommendations


def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def _safe_select(path: str) -> list[dict]:
    from scripts.prelaunch_utils import rest_select

    try:
        return rest_select(path) or []
    except Exception:
        return []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_ops_monitor_summary(send_report_email: Callable[[str, str], Any] | None = None) -> dict[str, Any]:
    if not _flag("OPS_MONITOR_AGENT_ENABLED", "false"):
        return {
            "ok": False,
            "error": "ops_monitor_disabled",
            "read_only": True,
            "approval_required": False,
            "can_execute": False,
            "timestamp": _now(),
        }

    read_only = _flag("OPS_MONITOR_READ_ONLY", "true")
    swarm_dry_run = _flag("SWARM_DRY_RUN", "true")
    swarm_execution_enabled = _flag("SWARM_EXECUTION_ENABLED", "false")

    memory = hermes_ops_memory.load_memory(updated_by="ops_monitor_agent")

    heartbeats = _safe_select("worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=40")
    queue_rows = _safe_select("job_queue?select=id,status,created_at&order=created_at.desc&limit=80")
    workflow_rows = _safe_select("workflow_outputs?select=id,summary,status,created_at&order=created_at.desc&limit=50")
    approvals = _safe_select("owner_approval_queue?select=id,action_type,status,created_at&status=eq.pending&limit=20")
    health_rows = _safe_select("system_events?select=id,event_type,status,created_at&order=created_at.desc&limit=60")

    queue_summary: dict[str, int] = {}
    for row in queue_rows:
        key = str(row.get("status") or "unknown").lower()
        queue_summary[key] = queue_summary.get(key, 0) + 1

    failed = [r for r in workflow_rows if str(r.get("status") or "").lower() == "failed"]
    completed = [r for r in workflow_rows if str(r.get("status") or "").lower() in {"completed", "approved", "ready"}]

    worker_summary: dict[str, int] = {}
    for row in heartbeats:
        key = str(row.get("status") or "unknown").lower()
        worker_summary[key] = worker_summary.get(key, 0) + 1

    active_session = hermes_ops_memory.get_active_work_session(memory)
    blocked_items = list(memory.get("blocked_priorities") or [])
    recommended_next_action = (
        "Review pending approvals first." if approvals
        else ("Investigate latest failed workflow." if failed else "Continue top active priority.")
    )

    summary = {
        "run_id": f"opsmon_{int(datetime.now().timestamp())}",
        "timestamp": _now(),
        "read_only": True,
        "approval_required": False,
        "can_execute": False,
        "swarm_execution_enabled": False,
        "swarm_dry_run": swarm_dry_run,
        "worker_status_summary": worker_summary,
        "queue_summary": queue_summary,
        "recent_failures": failed[:8],
        "recent_completed": completed[:8],
        "pending_approvals": approvals[:8],
        "system_health_events": health_rows[:8],
        "active_work_session": active_session,
        "blocked_items": blocked_items,
        "recommended_next_action": recommended_next_action,
        "knowledge_recommendations": get_recent_recommendations(limit=5),
    }

    email_subject = f"Nexus Ops Monitor Summary - {summary['timestamp']}"
    email_body = "\n".join([
        "Nexus Ops Monitor Summary",
        f"Timestamp: {summary['timestamp']}",
        f"Read-only: {read_only}",
        f"Swarm dry run: {swarm_dry_run}",
        f"Swarm execution enabled: {swarm_execution_enabled}",
        f"Worker status: {summary['worker_status_summary']}",
        f"Queue summary: {summary['queue_summary']}",
        f"Recent failures: {len(summary['recent_failures'])}",
        f"Recent completed: {len(summary['recent_completed'])}",
        f"Pending approvals: {len(summary['pending_approvals'])}",
        f"Blocked items: {len(summary['blocked_items'])}",
        f"Recommended next action: {summary['recommended_next_action']}",
        f"Knowledge recommendations: {len(summary['knowledge_recommendations'])}",
    ])

    email_status = {"subject": email_subject, "sent": False, "configured": False, "error": "not_attempted", "provider": "smtp_gmail", "recipient_masked": "not-set"}
    if send_report_email:
        result = send_report_email(email_subject, email_body)
        if isinstance(result, dict):
            email_status.update(result)
            email_status["subject"] = email_subject
        else:
            email_status.update({"sent": True, "configured": True, "error": ""})

    memory["latest_ops_monitor_run"] = {
        "timestamp": summary["timestamp"],
        "worker_status_summary": summary["worker_status_summary"],
        "queue_summary": summary["queue_summary"],
        "recent_failures_count": len(summary["recent_failures"]),
        "pending_approvals_count": len(summary["pending_approvals"]),
        "recommended_next_action": summary["recommended_next_action"],
        "read_only": True,
    }
    hermes_ops_memory.save_memory(memory, updated_by="ops_monitor_agent")

    return {
        "ok": True,
        "read_only": True,
        "approval_required": False,
        "can_execute": False,
        "dry_run_only": True,
        "timestamp": summary["timestamp"],
        "summary": summary,
        "email": email_status,
    }
