"""
Worker Accountability System
==============================
Tracks real worker productivity, generates daily rollups, and detects
idle or failing workers.

Every worker must have:
  - assigned role
  - active queue
  - last completed task
  - current task
  - productivity score
  - execution history
  - operational heartbeat
  - failure tracking

Usage:
  from lib.worker_accountability import rollup_worker_productivity, get_productivity_report
  rollup_worker_productivity()
  report = get_productivity_report()
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, date, timedelta, timezone
from typing import Any

WORKER_ROLES = {
    "opencode_codex": "Implementation Operator",
    "claude_code": "Architecture Designer",
    "openclaude": "Review & Refinement",
    "hermes_gateway": "Chief of Staff / Intelligence",
    "opportunity_worker": "Opportunity Intelligence",
    "research_worker": "Research Intelligence",
    "content_worker": "Content Engine",
    "provider_health_worker": "Infrastructure Monitor",
    "coordination_worker": "Workflow Coordinator",
    "optimization_worker": "Optimization Engine",
    "improvement_worker": "Autonomous Improvement",
    "user_intelligence_worker": "User Intelligence",
    "playlist_ingest_worker": "Content Ingestion",
    "ceo_brief_worker": "CEO Intelligence",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _sb_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").strip()


def _sb_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )


def _sb_get(path: str, timeout: int = 10) -> list:
    try:
        from scripts.prelaunch_utils import rest_select
        return rest_select(path, timeout=timeout) or []
    except Exception:
        return []


def _sb_upsert(table: str, payload: dict, conflict_cols: str = "") -> dict:
    url = _sb_url()
    key = _sb_key()
    if not url or not key:
        return {"error": "supabase_not_configured"}
    endpoint = f"{url}/rest/v1/{table}"
    prefer = "return=representation"
    if conflict_cols:
        prefer += f",resolution=merge-duplicates"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"error": str(exc)}


def _compute_productivity_score(
    completed: int, failed: int, planned: int,
    false_completions: int, evidence_ratio: float
) -> float:
    """
    Score 0–100 based on:
      - Task completion volume (40%)
      - Failure rate penalty (20%)
      - Evidence quality (30%)
      - False completion penalty (10%)
    """
    total = completed + failed + planned
    if total == 0:
        return 0.0

    completion_rate = completed / max(total, 1)
    failure_penalty = failed / max(total, 1)
    false_penalty = false_completions / max(completed + false_completions, 1)

    score = (
        completion_rate * 40.0
        + (1 - failure_penalty) * 20.0
        + evidence_ratio * 30.0
        + (1 - false_penalty) * 10.0
    )
    return round(min(100.0, max(0.0, score)), 2)


def rollup_worker_productivity(report_date: str | None = None) -> list[dict]:
    """
    Compute daily productivity rollup for all known workers.
    Saves to worker_productivity_rollups. Returns list of rollup dicts.
    """
    d = report_date or _today()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # All dispatch tasks for today
    tasks = _sb_get(
        f"agent_dispatch_tasks?select=id,status,source,task_type,false_completion,"
        f"evidence_type,created_at,completed_at"
        f"&created_at=gte.{d}T00:00:00Z&order=created_at.asc&limit=500"
    )

    # Group by source (worker_id)
    from collections import defaultdict
    by_worker: dict[str, list] = defaultdict(list)
    for t in tasks:
        src = str(t.get("source") or "unknown")
        by_worker[src].append(t)

    # Also pick up heartbeats
    heartbeats = _sb_get(
        "worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=60"
    )
    hb_map = {h["worker_id"]: h for h in heartbeats if h.get("worker_id")}

    rollups = []
    all_worker_ids = set(by_worker.keys()) | set(hb_map.keys())

    for wid in all_worker_ids:
        worker_tasks = by_worker.get(wid, [])
        hb = hb_map.get(wid, {})

        completed = sum(1 for t in worker_tasks if str(t.get("status","")).startswith("completed"))
        failed = sum(1 for t in worker_tasks if t.get("status") == "failed")
        planned = sum(1 for t in worker_tasks if t.get("status") == "planned")
        awaiting = sum(1 for t in worker_tasks if t.get("status") == "awaiting_approval")
        false_c = sum(1 for t in worker_tasks if t.get("false_completion"))
        with_evidence = sum(1 for t in worker_tasks if t.get("evidence_type") and str(t.get("status","")).startswith("completed"))
        evidence_ratio = (with_evidence / max(completed, 1)) if completed > 0 else 0.0

        score = _compute_productivity_score(completed, failed, planned, false_c, evidence_ratio)

        rollup = {
            "report_date": d,
            "worker_id": wid,
            "worker_role": WORKER_ROLES.get(wid, "Specialist"),
            "tasks_completed": completed,
            "tasks_failed": failed,
            "tasks_planned": planned,
            "tasks_awaiting": awaiting,
            "productivity_score": score,
            "evidence_ratio": round(evidence_ratio * 100, 2),
            "false_completion_count": false_c,
            "last_heartbeat_at": hb.get("last_seen_at"),
            "is_active": str(hb.get("status","")).lower() == "active" or completed > 0,
        }
        _sb_upsert("worker_productivity_rollups", rollup, conflict_cols="report_date,worker_id")
        rollups.append(rollup)

    return rollups


def get_productivity_report(days: int = 7) -> str:
    """Return a formatted markdown productivity report for the last N days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    rollups = _sb_get(
        f"worker_productivity_rollups?select=report_date,worker_id,worker_role,"
        f"tasks_completed,tasks_failed,productivity_score,false_completion_count"
        f"&report_date=gte.{since}&order=report_date.desc,productivity_score.desc&limit=100"
    )

    if not rollups:
        return f"No productivity data found for the last {days} days."

    lines = [
        f"# Worker Productivity Report — Last {days} Days",
        f"Generated: {_now()}",
        "",
        "| Worker | Role | Completed | Failed | Score | False Completions |",
        "|--------|------|-----------|--------|-------|------------------|",
    ]
    for r in rollups:
        lines.append(
            f"| {r.get('worker_id','?')} | {r.get('worker_role','?')} | "
            f"{r.get('tasks_completed',0)} | {r.get('tasks_failed',0)} | "
            f"{r.get('productivity_score',0):.1f} | {r.get('false_completion_count',0)} |"
        )
    lines += [
        "",
        f"Total rollup records: {len(rollups)}",
    ]
    return "\n".join(lines)


def get_worker_status(worker_id: str | None = None) -> list[dict]:
    """Return current status for one or all workers."""
    path = "worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=40"
    if worker_id:
        path += f"&worker_id=eq.{worker_id}"
    rows = _sb_get(path)
    return [
        {
            "worker_id": r.get("worker_id"),
            "role": WORKER_ROLES.get(str(r.get("worker_id","")), "Unknown"),
            "status": r.get("status"),
            "last_seen": r.get("last_seen_at"),
        }
        for r in rows
    ]


def assign_task_to_worker(
    worker_id: str,
    task_description: str,
    task_type: str = "general",
    priority: int = 5,
) -> dict:
    """
    Create an agent_dispatch_task assigned to a specific worker.
    Status starts as 'planned' — the worker must claim it.
    """
    url = _sb_url()
    key = _sb_key()
    if not url or not key:
        return {"error": "supabase_not_configured"}

    payload = {
        "source": worker_id,
        "original_prompt": task_description,
        "normalized_goal": task_description[:500],
        "task_type": task_type,
        "risk_level": "low",
        "status": "planned",
        "approval_required": False,
        "created_at": _now(),
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/agent_dispatch_tasks",
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            if isinstance(result, list):
                return result[0] if result else {}
            return result
    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    print("Computing productivity rollups...")
    rollups = rollup_worker_productivity()
    print(f"Rolled up {len(rollups)} workers")
    print()
    print(get_productivity_report(days=7))
