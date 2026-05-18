"""
Admin API — Agent Dispatch Routes.

Provides REST endpoints for the Nexus Workforce Command Center UI.

Routes (Flask/FastAPI style — adapt to your server framework):
    GET  /api/admin/agent-dispatch/resources
    GET  /api/admin/agent-dispatch/tasks
    POST /api/admin/agent-dispatch/tasks
    POST /api/admin/agent-dispatch/tasks/:id/plan
    GET  /api/admin/agent-dispatch/approvals
    POST /api/admin/agent-dispatch/approvals/:id/approve
    POST /api/admin/agent-dispatch/approvals/:id/reject

All write operations return {"ok": true, "id": ...} on success.
All functions follow the safety rules: no auto-approval, no live execution.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("AgentDispatchAPI")

NEXUS_DRY_RUN = os.getenv("NEXUS_DRY_RUN", "true").lower() != "false"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sb_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip()


def _sb_key() -> str:
    return (os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_KEY", ""))


def _headers() -> dict[str, str]:
    key = _sb_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _get(path: str, timeout: int = 10) -> list[dict]:
    url = _sb_url()
    if not url:
        return []
    try:
        req = urllib.request.Request(f"{url}/rest/v1/{path}", headers=_headers())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()) or []
    except Exception as e:
        logger.warning("GET %s failed: %s", path, e)
        return []


def _post(table: str, payload: dict, timeout: int = 10) -> dict:
    url = _sb_url()
    if not url:
        return {"error": "supabase_not_configured"}
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/{table}", data=data, headers=_headers(), method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            result = json.loads(r.read())
            return result[0] if isinstance(result, list) and result else {}
    except Exception as e:
        logger.error("POST %s failed: %s", table, e)
        return {"error": str(e)}


def _patch(table: str, match_key: str, match_val: str, payload: dict, timeout: int = 10) -> bool:
    url = _sb_url()
    if not url:
        return False
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/{table}?{match_key}=eq.{match_val}",
            data=data,
            headers={**_headers(), "Prefer": ""},
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
        return True
    except Exception as e:
        logger.error("PATCH %s failed: %s", table, e)
        return False


# ─── Route handlers ───────────────────────────────────────────────────────────

def get_resources() -> dict[str, Any]:
    """
    GET /api/admin/agent-dispatch/resources

    Returns all registered agents, skills, and CLI tools.
    Used by the Resource Registry tab in Workforce Command Center.
    """
    agents = _get("agent_capabilities?select=*&order=priority")
    skills = _get("nexus_skills?select=*&order=category")
    cli_tools = _get("nexus_cli_tools?select=*&order=cli_key")
    providers = _get("provider_health?select=*&order=provider_name")

    return {
        "agents": agents,
        "skills": skills,
        "cli_tools": cli_tools,
        "providers": providers,
        "counts": {
            "agents": len(agents),
            "skills": len(skills),
            "cli_tools": len(cli_tools),
            "providers": len(providers),
        },
        "generated_at": _now(),
    }


def list_tasks(
    status: str | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    """
    GET /api/admin/agent-dispatch/tasks[?status=received&limit=30]

    Returns dispatch tasks, optionally filtered by status.
    """
    qs = f"agent_dispatch_tasks?select=*&order=created_at.desc&limit={limit}"
    if status:
        qs += f"&status=eq.{status}"
    tasks = _get(qs)
    return {"tasks": tasks, "total": len(tasks), "generated_at": _now()}


def create_task(
    prompt: str,
    task_type: str | None = None,
    requested_by: str = "admin",
) -> dict[str, Any]:
    """
    POST /api/admin/agent-dispatch/tasks

    Creates a new dispatch task. Classifies type and risk, then inserts into DB.
    High/critical risk tasks go straight to awaiting_approval.
    """
    try:
        from lib.agent_dispatcher.risk import assess_risk
        from lib.agent_dispatcher.planner import classify_task_type
        resolved_type = task_type or classify_task_type(prompt)
        risk = assess_risk(prompt, resolved_type)
    except Exception as e:
        logger.warning("Dispatcher unavailable: %s", e)
        resolved_type = task_type or "general"
        risk = {"level": "low", "requires_approval": False, "blocked": False}

    if risk.get("blocked"):
        return {
            "ok": False,
            "error": "blocked",
            "reason": risk.get("block_reason", "Hard-blocked by safety rules"),
        }

    status = "awaiting_approval" if risk.get("requires_approval") else "received"
    payload = {
        "prompt": prompt,
        "task_type": resolved_type,
        "risk_level": risk.get("level", "low"),
        "status": status,
        "requires_approval": risk.get("requires_approval", False),
        "requested_by": requested_by,
        "dry_run": NEXUS_DRY_RUN,
        "created_at": _now(),
    }
    result = _post("agent_dispatch_tasks", payload)
    if result.get("error"):
        return {"ok": False, "error": result["error"]}
    return {"ok": True, "id": result.get("id"), "status": status, "risk_level": risk.get("level")}


def plan_task(task_id: str) -> dict[str, Any]:
    """
    POST /api/admin/agent-dispatch/tasks/:id/plan

    Runs the planner on an existing task and creates subtasks.
    Requires the task to be in 'received' or 'needs_clarification' state.
    """
    tasks = _get(f"agent_dispatch_tasks?select=*&id=eq.{task_id}&limit=1")
    if not tasks:
        return {"ok": False, "error": "task_not_found"}
    task = tasks[0]

    if task.get("status") not in {"received", "needs_clarification"}:
        return {"ok": False, "error": f"task_status={task.get('status')} not plannable"}

    try:
        from lib.agent_dispatcher.planner import build_task_plan
        from lib.agent_dispatcher.router import route_subtask
        plan = build_task_plan(task.get("prompt", ""), task.get("task_type", "general"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

    subtasks_created: list[dict] = []
    for i, st in enumerate(plan.get("subtasks", [])):
        routed = route_subtask(st)
        payload = {
            "parent_task_id": task_id,
            "sequence_order": i + 1,
            "task_type": st.get("task_type", "general"),
            "prompt_summary": st.get("prompt_summary", ""),
            "assigned_agent_key": routed.get("assigned_agent_key"),
            "assigned_skill_key": routed.get("assigned_skill_key"),
            "assigned_cli_key": routed.get("assigned_cli_key"),
            "assigned_provider_key": routed.get("assigned_provider_key"),
            "risk_level": routed.get("risk_level", "low"),
            "requires_approval": routed.get("requires_approval", False),
            "status": "awaiting_approval" if routed.get("requires_approval") else "planned",
            "routing_reason": routed.get("routing_reason", ""),
            "created_at": _now(),
        }
        result = _post("agent_dispatch_subtasks", payload)
        if not result.get("error"):
            subtasks_created.append(result)

    _patch("agent_dispatch_tasks", "id", task_id, {"status": "planning", "updated_at": _now()})

    return {
        "ok": True,
        "task_id": task_id,
        "subtasks_created": len(subtasks_created),
        "needs_clarification": plan.get("needs_clarification", False),
        "clarification_question": plan.get("clarification_question", ""),
    }


def list_approvals(limit: int = 20) -> dict[str, Any]:
    """
    GET /api/admin/agent-dispatch/approvals

    Returns pending human approval requests.
    """
    rows = _get(
        f"human_approval_requests?select=*&status=eq.pending&order=created_at.desc&limit={limit}"
    )
    return {"approvals": rows, "total": len(rows), "generated_at": _now()}


def approve_request(approval_id: str, reviewed_by: str = "admin") -> dict[str, Any]:
    """
    POST /api/admin/agent-dispatch/approvals/:id/approve

    Approves a pending human approval request.
    Safety: only marks as approved — does not auto-execute anything.
    """
    ok = _patch(
        "human_approval_requests",
        "id",
        approval_id,
        {"status": "approved", "reviewed_at": _now(), "reviewed_by": reviewed_by},
    )
    if not ok:
        return {"ok": False, "error": "patch_failed"}
    logger.info("approval_approved id=%s by=%s", approval_id, reviewed_by)
    return {"ok": True, "id": approval_id, "status": "approved"}


def reject_request(approval_id: str, reviewed_by: str = "admin", reason: str = "") -> dict[str, Any]:
    """
    POST /api/admin/agent-dispatch/approvals/:id/reject

    Rejects a pending human approval request.
    """
    payload: dict[str, Any] = {
        "status": "rejected",
        "reviewed_at": _now(),
        "reviewed_by": reviewed_by,
    }
    if reason:
        payload["rejection_reason"] = reason
    ok = _patch("human_approval_requests", "id", approval_id, payload)
    if not ok:
        return {"ok": False, "error": "patch_failed"}
    logger.info("approval_rejected id=%s by=%s", approval_id, reviewed_by)
    return {"ok": True, "id": approval_id, "status": "rejected"}
