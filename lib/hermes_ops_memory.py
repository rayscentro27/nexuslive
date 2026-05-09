from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("HermesOpsMemory")

ROOT = Path(__file__).resolve().parent.parent
LOCAL_MEMORY_FILE = ROOT / ".hermes_ops_memory.json"
EVENT_TYPE = "hermes_ops_memory_snapshot"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_memory() -> dict[str, Any]:
    return {
        "plan_id": "",
        "latest_daily_plan": [],
        "active_priorities": [],
        "recent_recommendations": [],
        "task_lifecycle": {},
        "task_lifecycle_summary": {
            "queued": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "canceled": 0,
            "blocked": 0,
        },
        "recent_completed": [],
        "recent_failed": [],
        "blocked_priorities": [],
        "completed_priorities": [],
        "pending_approval": None,
        "pending_approval_refs": [],
        "updated_at": _now(),
        "updated_by": "system",
        "last_user_instruction": "",
        "work_sessions": [],
        "active_work_session_id": None,
        "latest_ops_monitor_run": None,
    }


def _supabase_env() -> tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return url, key


def _sb_get(path: str, timeout: int = 8) -> list[dict]:
    url, key = _supabase_env()
    if not url or not key:
        return []
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
            return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _sb_post(path: str, body: dict, timeout: int = 8) -> bool:
    url, key = _supabase_env()
    if not url or not key:
        return False
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except urllib.error.HTTPError as e:
        logger.warning("memory snapshot post failed: %s", e.code)
        return False
    except Exception:
        return False


def _recompute_summary(memory: dict[str, Any]) -> None:
    lifecycle = memory.get("task_lifecycle") or {}
    states = [str(v).strip().lower() for v in lifecycle.values()]
    memory["task_lifecycle_summary"] = {
        "queued": sum(1 for s in states if s in {"queued", "pending", "waiting_for_approval"}),
        "running": sum(1 for s in states if s == "running"),
        "completed": sum(1 for s in states if s == "completed"),
        "failed": sum(1 for s in states if s == "failed"),
        "canceled": sum(1 for s in states if s in {"canceled", "cancelled"}),
        "blocked": sum(1 for s in states if s == "blocked"),
    }


def _read_local() -> dict[str, Any]:
    if not LOCAL_MEMORY_FILE.exists():
        return _default_memory()
    try:
        payload = json.loads(LOCAL_MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            mem = _default_memory()
            mem.update(payload)
            _recompute_summary(mem)
            return mem
    except Exception:
        pass
    return _default_memory()


def _write_local(memory: dict[str, Any]) -> None:
    LOCAL_MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding="utf-8")


def _latest_supabase_snapshot() -> dict[str, Any] | None:
    rows = _sb_get(
        f"system_events?event_type=eq.{EVENT_TYPE}&select=payload,created_at&order=created_at.desc&limit=1"
    )
    if not rows:
        return None
    payload = rows[0].get("payload")
    if isinstance(payload, dict):
        mem = _default_memory()
        mem.update(payload)
        _recompute_summary(mem)
        return mem
    return None


def _append_supabase_snapshot(memory: dict[str, Any]) -> bool:
    row = {
        "event_type": EVENT_TYPE,
        "status": "completed",
        "payload": memory,
    }
    return _sb_post("system_events", row)


def _reconcile_live(memory: dict[str, Any]) -> dict[str, Any]:
    out = dict(memory)
    approvals = _sb_get("owner_approval_queue?select=id,status,action_type,created_at&status=eq.pending&limit=20")
    out["pending_approval_refs"] = [
        {
            "id": r.get("id"),
            "status": r.get("status"),
            "action_type": r.get("action_type"),
            "created_at": r.get("created_at"),
        }
        for r in approvals
    ]
    if approvals and not out.get("pending_approval"):
        out["pending_approval"] = {
            "task": approvals[0].get("action_type", "approval_required"),
            "reason": "Pending owner approval.",
        }

    tasks = _sb_get(
        "system_events?select=id,status&event_type=eq.ceo_route_request&order=created_at.desc&limit=100"
    )
    live_lifecycle = dict(out.get("task_lifecycle") or {})
    for row in tasks:
        sid = str(row.get("id") or "")
        status = str(row.get("status") or "").lower()
        if not sid:
            continue
        mapped = {
            "pending": "queued",
            "claimed": "running",
            "completed": "completed",
            "failed": "failed",
        }.get(status, status or "queued")
        live_lifecycle[sid] = mapped
    out["task_lifecycle"] = live_lifecycle

    workflow_rows = _sb_get("workflow_outputs?select=status,summary,created_at&order=created_at.desc&limit=20")
    if workflow_rows:
        failed = [r for r in workflow_rows if str(r.get("status", "")).lower() == "failed"]
        for row in failed[:3]:
            out.setdefault("recent_failed", []).append(
                {
                    "task": row.get("summary") or "workflow output",
                    "reason": "workflow_failed",
                    "timestamp": row.get("created_at") or _now(),
                    "retry_recommendation": "Review workflow output and retry after fix.",
                }
            )

    _recompute_summary(out)
    return out


def load_memory(updated_by: str = "system") -> dict[str, Any]:
    supa = _latest_supabase_snapshot()
    mem = supa or _read_local()
    mem = _reconcile_live(mem)
    mem["updated_by"] = updated_by
    mem["updated_at"] = _now()
    _write_local(mem)
    return mem


def save_memory(memory: dict[str, Any], updated_by: str = "system") -> dict[str, Any]:
    out = _default_memory()
    out.update(memory or {})
    out["updated_by"] = updated_by
    out["updated_at"] = _now()
    _recompute_summary(out)
    _write_local(out)
    if not _append_supabase_snapshot(out):
        logger.warning("supabase unavailable; memory persisted locally only")
    return out


def _new_session(current_goal: str, memory: dict[str, Any]) -> dict[str, Any]:
    ts = int(datetime.now().timestamp())
    return {
        "session_id": f"ws_{ts}",
        "started_at": _now(),
        "updated_at": _now(),
        "status": "active",
        "current_goal": current_goal.strip() or "Maintain operational progress.",
        "active_tasks": list(memory.get("active_priorities") or []),
        "pending_approvals": list(memory.get("pending_approval_refs") or []),
        "blocked_items": list(memory.get("blocked_priorities") or []),
        "completed_items": list(memory.get("recent_completed") or [])[-5:],
        "failed_items": list(memory.get("recent_failed") or [])[-5:],
        "next_recommended_action": (list(memory.get("recent_recommendations") or ["Review top active priority"]) or ["Review top active priority"])[0],
    }


def _sessions(memory: dict[str, Any]) -> list[dict]:
    sessions = memory.get("work_sessions")
    if isinstance(sessions, list):
        return sessions
    memory["work_sessions"] = []
    return memory["work_sessions"]


def get_active_work_session(memory: dict[str, Any]) -> dict[str, Any] | None:
    sid = memory.get("active_work_session_id")
    sessions = _sessions(memory)
    for s in sessions:
        if s.get("session_id") == sid:
            return s
    for s in reversed(sessions):
        if s.get("status") == "active":
            memory["active_work_session_id"] = s.get("session_id")
            return s
    return None


def start_work_session(memory: dict[str, Any], current_goal: str, updated_by: str = "system") -> dict[str, Any]:
    sessions = _sessions(memory)
    active = get_active_work_session(memory)
    if active:
        active["updated_at"] = _now()
        active["current_goal"] = current_goal.strip() or active.get("current_goal")
        memory["active_work_session_id"] = active.get("session_id")
        return save_memory(memory, updated_by=updated_by)
    session = _new_session(current_goal, memory)
    sessions.append(session)
    memory["active_work_session_id"] = session["session_id"]
    return save_memory(memory, updated_by=updated_by)


def pause_work_session(memory: dict[str, Any], updated_by: str = "system") -> dict[str, Any]:
    session = get_active_work_session(memory)
    if session:
        session["status"] = "paused"
        session["updated_at"] = _now()
    memory["active_work_session_id"] = None
    return save_memory(memory, updated_by=updated_by)


def resume_work_session(memory: dict[str, Any], updated_by: str = "system") -> dict[str, Any]:
    sessions = _sessions(memory)
    for session in reversed(sessions):
        if session.get("status") in {"paused", "active"}:
            session["status"] = "active"
            session["updated_at"] = _now()
            session["active_tasks"] = list(memory.get("active_priorities") or [])
            session["pending_approvals"] = list(memory.get("pending_approval_refs") or [])
            session["blocked_items"] = list(memory.get("blocked_priorities") or [])
            session["completed_items"] = list(memory.get("recent_completed") or [])[-5:]
            session["failed_items"] = list(memory.get("recent_failed") or [])[-5:]
            memory["active_work_session_id"] = session.get("session_id")
            return save_memory(memory, updated_by=updated_by)
    return start_work_session(memory, "Resume previous priorities.", updated_by=updated_by)


def summarize_work_session(memory: dict[str, Any]) -> str:
    session = get_active_work_session(memory)
    if not session:
        sessions = _sessions(memory)
        if not sessions:
            return "No work session is active yet. Say 'start work session' to begin."
        latest = sessions[-1]
        return (
            f"Latest session is {latest.get('status', 'unknown')}. "
            f"Goal: {latest.get('current_goal', 'none')}."
        )
    return (
        f"Work session {session.get('session_id')} is active. "
        f"Goal: {session.get('current_goal')}. "
        f"Tasks: {len(session.get('active_tasks') or [])}, "
        f"approvals: {len(session.get('pending_approvals') or [])}, "
        f"blocked: {len(session.get('blocked_items') or [])}."
    )


def update_latest_daily_plan(memory: dict[str, Any], plan_items: list[str], updated_by: str = "system") -> dict[str, Any]:
    memory["latest_daily_plan"] = list(plan_items or [])
    memory["active_priorities"] = list(plan_items or [])
    memory["recent_recommendations"] = list(plan_items or [])
    memory["plan_id"] = f"plan_{int(datetime.now().timestamp())}"
    return save_memory(memory, updated_by=updated_by)


def update_task_lifecycle(memory: dict[str, Any], task_id: str, status: str, updated_by: str = "system") -> dict[str, Any]:
    if task_id:
        memory.setdefault("task_lifecycle", {})[task_id] = status
    return save_memory(memory, updated_by=updated_by)


def update_approval_state(memory: dict[str, Any], approval: dict[str, Any] | None, updated_by: str = "system") -> dict[str, Any]:
    memory["pending_approval"] = approval
    return save_memory(memory, updated_by=updated_by)


def record_completion(memory: dict[str, Any], task: str, updated_by: str = "system") -> dict[str, Any]:
    memory.setdefault("recent_completed", []).append({"task": task, "timestamp": _now()})
    if task in memory.get("active_priorities", []):
        memory["active_priorities"] = [t for t in memory.get("active_priorities", []) if t != task]
    if task and task not in memory.get("completed_priorities", []):
        memory.setdefault("completed_priorities", []).append(task)
    return save_memory(memory, updated_by=updated_by)


def record_failure(memory: dict[str, Any], task: str, reason: str, retry_recommendation: str, updated_by: str = "system") -> dict[str, Any]:
    memory.setdefault("recent_failed", []).append(
        {
            "task": task,
            "reason": reason,
            "timestamp": _now(),
            "retry_recommendation": retry_recommendation,
        }
    )
    return save_memory(memory, updated_by=updated_by)


def summarize_current_work(memory: dict[str, Any]) -> str:
    active = memory.get("active_priorities") or []
    if not active:
        return "No active priorities are stored yet. Ask me for today's plan and I'll set them."
    return "We are working on: " + ", ".join(active[:3])


def summarize_pending_approvals(memory: dict[str, Any]) -> str:
    refs = memory.get("pending_approval_refs") or []
    if refs:
        return f"There are {len(refs)} approvals waiting right now."
    pending = memory.get("pending_approval")
    if pending:
        return "There is one approval waiting right now."
    return "No approvals are waiting right now."


def summarize_failed_today(memory: dict[str, Any]) -> str:
    failed = memory.get("recent_failed") or []
    if not failed:
        return "No failed tasks are recorded today."
    latest = failed[-1]
    return f"Latest failure: {latest.get('task', 'task')} - {latest.get('reason', 'unknown reason')}."


def resolve_plan_item_status(memory: dict[str, Any], item_number: int) -> str:
    plan = memory.get("latest_daily_plan") or []
    if item_number <= 0 or item_number > len(plan):
        return "I don't have that plan item stored yet."
    title = plan[item_number - 1]
    summary = memory.get("task_lifecycle_summary") or {}
    if summary.get("completed", 0) > 0:
        return f"Item {item_number} ({title}) has completed."
    if summary.get("running", 0) > 0 or summary.get("queued", 0) > 0:
        return f"Item {item_number} ({title}) is still in progress."
    return f"Item {item_number} ({title}) has not started yet."


def summarize_resume_previous_work(memory: dict[str, Any]) -> str:
    s = memory.get("task_lifecycle_summary") or {}
    approvals = summarize_pending_approvals(memory)
    return (
        f"Resuming previous work. Running: {s.get('running', 0)}. "
        f"Pending: {s.get('queued', 0)}. {approvals}"
    )
