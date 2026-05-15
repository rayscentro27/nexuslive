from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


ALLOWED_STATUSES = {
    "queued",
    "assigned",
    "running",
    "waiting_review",
    "completed",
    "failed",
    "rejected",
    "paused",
}

WORKER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "opencode_codex": {
        "role": "implementation_operator",
        "specialties": ["repo operations", "scripts", "terminal ops", "tests", "audits", "infrastructure"],
        "capabilities": ["code changes", "test execution", "report writing", "safe git workflow"],
        "allowed_actions": ["read", "write", "test", "report", "safe_branch_commit"],
        "active": True,
        "health_status": "ready",
        "concurrency_limit": 2,
        "runtime_environment": "local_cli",
    },
    "claude_code": {
        "role": "architecture_designer",
        "specialties": ["ui ux", "architecture", "complex feature passes", "system design", "visual systems"],
        "capabilities": ["design planning", "implementation guidance", "review"],
        "allowed_actions": ["read", "write", "test", "report", "safe_branch_commit"],
        "active": True,
        "health_status": "ready",
        "concurrency_limit": 2,
        "runtime_environment": "external_cli",
    },
    "openclaude": {
        "role": "review_refinement",
        "specialties": ["backup reviewer", "refinement", "fallback implementation", "second-pass analysis"],
        "capabilities": ["review", "refactor", "summary"],
        "allowed_actions": ["read", "write", "test", "report"],
        "active": True,
        "health_status": "ready",
        "concurrency_limit": 1,
        "runtime_environment": "external_cli",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sb_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip()


def _sb_key() -> str:
    return os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")


def _headers() -> dict[str, str]:
    key = _sb_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _enabled() -> bool:
    return bool(_sb_url() and _sb_key())


def _sb_get(table_query: str) -> list[dict[str, Any]]:
    if not _enabled():
        return []
    url = f"{_sb_url()}/rest/v1/{table_query}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read())
    except Exception:
        return []


def _sb_post(table: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not _enabled():
        return None
    url = f"{_sb_url()}/rest/v1/{table}"
    req = urllib.request.Request(url, method="POST", data=json.dumps(payload).encode("utf-8"), headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            rows = json.loads(resp.read())
            return rows[0] if rows else None
    except Exception:
        return None


def _sb_patch(table: str, where: dict[str, str], payload: dict[str, Any]) -> bool:
    if not _enabled():
        return False
    query = urllib.parse.urlencode({k: f"eq.{v}" for k, v in where.items()})
    url = f"{_sb_url()}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, method="PATCH", data=json.dumps(payload).encode("utf-8"), headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=12):
            return True
    except Exception:
        return False


def requires_manual_approval(task_type: str, instructions: str) -> bool:
    text = f"{task_type} {instructions}".lower()
    blocked = [
        "production deploy",
        "deploy to production",
        "delete schema",
        "drop table",
        "real money trading",
        "env modification",
        "update .env",
        "payment integration",
        "destructive repo",
        "reset --hard",
    ]
    return any(k in text for k in blocked)


def suggest_worker(task_text: str) -> str:
    t = task_text.lower()
    if any(k in t for k in ["ui", "ux", "redesign", "visual", "architecture", "system design"]):
        return "claude_code"
    if any(k in t for k in ["review", "refine", "second pass", "fallback"]):
        return "openclaude"
    return "opencode_codex"


def create_task(
    *,
    created_by: str,
    source: str,
    title: str,
    instructions: str,
    task_type: str = "coding",
    priority: str = "medium",
    assigned_worker: str | None = None,
    repo_target: str = "nexus-ai",
    estimated_scope: str = "medium",
) -> dict[str, Any]:
    worker = assigned_worker or suggest_worker(f"{title} {instructions}")
    needs_approval = requires_manual_approval(task_type, instructions)
    payload = {
        "created_by": created_by,
        "source": source,
        "assigned_worker": worker,
        "task_type": task_type,
        "priority": priority,
        "title": title,
        "instructions": instructions,
        "status": "queued",
        "created_at": _now(),
        "requires_approval": needs_approval,
        "repo_target": repo_target,
        "estimated_scope": estimated_scope,
    }
    row = _sb_post("ai_task_queue", payload)
    if row:
        _sb_post(
            "ai_task_activity_log",
            {
                "task_id": row.get("id"),
                "worker_id": worker,
                "activity_type": "task_created",
                "activity_summary": f"Task queued from {source}",
                "created_at": _now(),
            },
        )
        return row
    return {"id": "local-only", **payload}


def list_tasks(status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    q = "ai_task_queue?select=id,title,assigned_worker,status,priority,created_at,completed_at,result_summary&order=created_at.desc"
    if status:
        q += f"&status=eq.{status}"
    q += f"&limit={max(1, min(limit, 100))}"
    return _sb_get(q)


def claim_next_task(worker_id: str) -> dict[str, Any] | None:
    rows = _sb_get(
        "ai_task_queue?select=id,title,instructions,assigned_worker,status,requires_approval,created_at&status=eq.queued"
        f"&assigned_worker=eq.{urllib.parse.quote(worker_id, safe='')}&order=created_at.asc&limit=1"
    )
    if not rows:
        return None
    task = rows[0]
    if bool(task.get("requires_approval")):
        _sb_patch("ai_task_queue", {"id": str(task.get("id"))}, {"status": "waiting_review", "started_at": _now()})
        return {**task, "status": "waiting_review"}

    claimed = _sb_patch(
        "ai_task_queue",
        {"id": str(task.get("id")), "status": "queued"},
        {"status": "running", "started_at": _now()},
    )
    if not claimed:
        return None
    _sb_post(
        "ai_task_activity_log",
        {
            "task_id": task.get("id"),
            "worker_id": worker_id,
            "activity_type": "task_claimed",
            "activity_summary": "Worker claimed task",
            "created_at": _now(),
        },
    )
    task["status"] = "running"
    return task


def complete_task(task_id: str, worker_id: str, result_summary: str, status: str = "completed", error_summary: str = "") -> bool:
    if status not in ALLOWED_STATUSES:
        status = "failed"
    ok = _sb_patch(
        "ai_task_queue",
        {"id": task_id},
        {
            "status": status,
            "completed_at": _now(),
            "result_summary": result_summary,
            "error_summary": error_summary,
        },
    )
    if ok:
        _sb_post(
            "ai_task_results",
            {
                "task_id": task_id,
                "worker_id": worker_id,
                "status": status,
                "result_summary": result_summary,
                "error_summary": error_summary,
                "created_at": _now(),
            },
        )
        _sb_post(
            "ai_task_activity_log",
            {
                "task_id": task_id,
                "worker_id": worker_id,
                "activity_type": "task_completed" if status == "completed" else "task_failed",
                "activity_summary": result_summary[:300],
                "created_at": _now(),
            },
        )
    return ok


def pause_worker_tasks(worker_id: str) -> int:
    rows = _sb_get(f"ai_task_queue?select=id,status&assigned_worker=eq.{urllib.parse.quote(worker_id, safe='')}&status=in.(queued,assigned,running)")
    updated = 0
    for row in rows:
        if _sb_patch("ai_task_queue", {"id": str(row.get("id"))}, {"status": "paused"}):
            updated += 1
    return updated


def resume_worker_tasks(worker_id: str) -> int:
    rows = _sb_get(f"ai_task_queue?select=id,status&assigned_worker=eq.{urllib.parse.quote(worker_id, safe='')}&status=eq.paused")
    updated = 0
    for row in rows:
        if _sb_patch("ai_task_queue", {"id": str(row.get("id"))}, {"status": "queued"}):
            updated += 1
    return updated


def worker_registry_rows() -> list[dict[str, Any]]:
    rows = []
    for worker_id, meta in WORKER_DEFINITIONS.items():
        rows.append({"worker_id": worker_id, **meta})
    return rows
