from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ai_task_dispatch import create_task


ROOT = Path(__file__).resolve().parent.parent
ROADMAP_PATH = ROOT / "roadmap" / "nexus_dynamic_roadmap.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_roadmap() -> dict[str, Any]:
    return _read_json(ROADMAP_PATH, {"updated_at": _now(), "tasks": [], "lessons": []})


def save_roadmap(data: dict[str, Any]) -> None:
    data["updated_at"] = _now()
    _write_json(ROADMAP_PATH, data)


def roadmap_summary() -> dict[str, Any]:
    data = load_roadmap()
    tasks = data.get("tasks") or []
    counts: dict[str, int] = {}
    for t in tasks:
        s = str(t.get("status") or "queued")
        counts[s] = counts.get(s, 0) + 1
    top = sorted(tasks, key=lambda x: int(x.get("priority_score") or 0), reverse=True)[:8]
    return {
        "total_tasks": len(tasks),
        "status_counts": counts,
        "top_priorities": top,
        "lessons": (data.get("lessons") or [])[-8:],
        "updated_at": data.get("updated_at"),
    }


def next_steps(limit: int = 20) -> list[dict[str, Any]]:
    tasks = load_roadmap().get("tasks") or []
    actionable = [t for t in tasks if str(t.get("status") or "queued") in {"queued", "active", "blocked", "paused", "review"}]
    ranked = sorted(actionable, key=lambda x: int(x.get("priority_score") or 0), reverse=True)
    return ranked[: max(1, min(limit, 50))]


def highest_priority_tasks(limit: int = 5) -> list[dict[str, Any]]:
    return next_steps(limit=limit)


def update_task_status(task_id: int, status: str) -> dict[str, Any] | None:
    if status not in {"queued", "active", "paused", "blocked", "review", "completed"}:
        return None
    data = load_roadmap()
    for t in data.get("tasks") or []:
        if int(t.get("id") or 0) == int(task_id):
            t["status"] = status
            t["updated_at"] = _now()
            save_roadmap(data)
            return t
    return None


def assign_task_to_worker(task_id: int) -> dict[str, Any] | None:
    data = load_roadmap()
    for t in data.get("tasks") or []:
        if int(t.get("id") or 0) == int(task_id):
            worker = str(t.get("recommended_worker") or "opencode_codex")
            dispatch = create_task(
                created_by="hermes_roadmap",
                source="telegram",
                title=str(t.get("title") or f"Roadmap task {task_id}"),
                instructions=str(t.get("next_suggested_discussion") or t.get("why_it_matters") or "Execute roadmap task"),
                assigned_worker=worker,
                task_type="roadmap_execution",
                priority="high" if int(t.get("priority_score") or 0) >= 85 else "medium",
                estimated_scope=str(t.get("estimated_scope") or "medium"),
            )
            t["status"] = "active"
            t["linked_dispatch_task_id"] = dispatch.get("id")
            t["updated_at"] = _now()
            save_roadmap(data)
            return {"roadmap_task": t, "dispatch_task": dispatch}
    return None


def systems_weaknesses(limit: int = 6) -> list[dict[str, Any]]:
    tasks = load_roadmap().get("tasks") or []
    weak = [t for t in tasks if str(t.get("status") or "") in {"blocked", "paused"}]
    return sorted(weak, key=lambda x: int(x.get("priority_score") or 0), reverse=True)[:limit]


def tester_readiness_view() -> dict[str, Any]:
    tasks = load_roadmap().get("tasks") or []
    tester = [t for t in tasks if "tester" in str(t.get("category") or "").lower() or "tester" in str(t.get("title") or "").lower()]
    done = len([t for t in tester if str(t.get("status") or "") == "completed"])
    return {
        "tester_tasks_total": len(tester),
        "tester_tasks_completed": done,
        "tester_readiness_percent": round((done / max(1, len(tester))) * 100, 2),
        "next_tester_priorities": sorted(tester, key=lambda x: int(x.get("priority_score") or 0), reverse=True)[:5],
    }
