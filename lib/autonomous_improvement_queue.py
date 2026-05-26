"""
Autonomous Improvement Queue
==============================
When workers are idle, they proactively pick safe improvement tasks.

Safe autonomous tasks (no approval required):
  - Identify broken links in docs
  - Improve SEO metadata
  - Generate draft content
  - Summarize new opportunities
  - Organize/clean stale docs
  - Generate recommendations
  - Audit affiliate system integrity
  - Review analytics / detect trends
  - Create worker recommendations
  - Audit incomplete systems

Unsafe (always require human approval):
  - Publishing to production
  - Billing / payments
  - Deployments
  - Deleting records
  - Auth / security changes
  - Financial transactions
  - Sending emails / Telegram messages

Usage:
  from lib.autonomous_improvement_queue import seed_improvement_tasks, claim_idle_task
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any

SAFE_TASK_TYPES = frozenset({
    "doc_audit",
    "seo_improvement",
    "draft_content",
    "opportunity_summary",
    "doc_organization",
    "recommendation_generation",
    "affiliate_audit",
    "analytics_review",
    "stale_record_cleanup",
    "system_audit",
    "link_check",
    "worker_report",
})

UNSAFE_REQUIRES_APPROVAL = frozenset({
    "publish",
    "billing",
    "deploy",
    "delete_records",
    "auth_change",
    "financial_action",
    "send_email",
    "send_telegram",
})

# Default improvement task templates
IMPROVEMENT_TASK_TEMPLATES = [
    {
        "task_type": "system_audit",
        "priority": "high",
        "title": "Audit agent_dispatch_tasks for false completions",
        "description": (
            "Query agent_dispatch_tasks WHERE status='completed' AND evidence_type IS NULL. "
            "Flag each as false_completion=true. Generate summary report."
        ),
        "estimated_minutes": 5,
    },
    {
        "task_type": "worker_report",
        "priority": "high",
        "title": "Generate daily worker productivity rollup",
        "description": (
            "Run lib.worker_accountability.rollup_worker_productivity() for today. "
            "Save rollups to worker_productivity_rollups. Return summary."
        ),
        "estimated_minutes": 3,
    },
    {
        "task_type": "opportunity_summary",
        "priority": "medium",
        "title": "Summarize top open recommendations",
        "description": (
            "Query worker_recommendations WHERE status='open' ORDER BY priority. "
            "Generate a concise summary of top 5 opportunities with estimated value."
        ),
        "estimated_minutes": 5,
    },
    {
        "task_type": "doc_audit",
        "priority": "medium",
        "title": "Audit Nexus docs for stale or duplicate files",
        "description": (
            "Scan /Users/raymonddavis/nexus-ai/docs/ for files older than 30 days with "
            "no recent reference. List candidates for archival. Do NOT delete."
        ),
        "estimated_minutes": 8,
    },
    {
        "task_type": "affiliate_audit",
        "priority": "medium",
        "title": "Review affiliate opportunity status",
        "description": (
            "Check NEXUS_AFFILIATE_ENGINE_ACTIVE.md and opportunity rankings. "
            "Report which affiliate programs have been applied to vs. pending."
        ),
        "estimated_minutes": 10,
    },
    {
        "task_type": "seo_improvement",
        "priority": "low",
        "title": "Generate SEO metadata for pending content drafts",
        "description": (
            "Query content_drafts WHERE status IN ('draft','ready') LIMIT 5. "
            "For each, generate: title tag, meta description, 5 keywords, slug. "
            "Save as draft — do NOT publish."
        ),
        "estimated_minutes": 15,
    },
    {
        "task_type": "analytics_review",
        "priority": "low",
        "title": "Review research artifact trends",
        "description": (
            "Query research_artifacts order by created_at DESC LIMIT 50. "
            "Identify top topic clusters and growth trends. "
            "Generate recommendation report to worker_recommendations."
        ),
        "estimated_minutes": 10,
    },
    {
        "task_type": "stale_record_cleanup",
        "priority": "low",
        "title": "Flag stale running tasks (>24h with no update)",
        "description": (
            "Query agent_dispatch_tasks WHERE status='running' "
            "AND updated_at < now() - interval '24 hours'. "
            "Update these to status='failed', add note 'stalled — auto-flagged by improvement worker'."
        ),
        "estimated_minutes": 3,
    },
    {
        "task_type": "recommendation_generation",
        "priority": "low",
        "title": "Generate weekly monetization recommendations",
        "description": (
            "Based on current opportunity rankings and content pipeline, "
            "generate 3 actionable monetization recommendations. "
            "Insert to worker_recommendations with evidence from Supabase data."
        ),
        "estimated_minutes": 15,
    },
    {
        "task_type": "link_check",
        "priority": "low",
        "title": "Validate all Nexus external links",
        "description": (
            "Check links in NEXUS_YOUTUBE_CHANNEL_AUDIT_2026_05.md and docs/. "
            "Report any 404s or redirect chains. "
            "Generate link_check_report.md in artifacts/."
        ),
        "estimated_minutes": 12,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sb_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").strip()


def _sb_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )


def _post(table: str, payload: dict) -> dict:
    url = _sb_url()
    key = _sb_key()
    if not url or not key:
        return {"error": "supabase_not_configured"}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}",
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
            return result[0] if isinstance(result, list) and result else result
    except Exception as exc:
        return {"error": str(exc)}


def _get(path: str) -> list:
    try:
        from scripts.prelaunch_utils import rest_select
        return rest_select(path, timeout=10) or []
    except Exception:
        return []


def seed_improvement_tasks(
    worker_id: str = "improvement_worker",
    limit: int = 3,
    priorities: list[str] | None = None,
) -> list[dict]:
    """
    Seed the task queue with improvement tasks for idle workers.
    Only seeds tasks not already in planned/running state.
    Returns list of created task dicts.
    """
    existing = _get(
        "agent_dispatch_tasks?select=normalized_goal,status"
        "&status=in.(planned,running,received)"
        "&source=eq.improvement_worker&limit=20"
    )
    existing_goals = {str(r.get("normalized_goal","")).lower().strip()[:80] for r in existing}

    filter_priorities = set(priorities or ["high", "medium", "low"])
    created = []

    for tmpl in IMPROVEMENT_TASK_TEMPLATES:
        if len(created) >= limit:
            break
        if tmpl["priority"] not in filter_priorities:
            continue
        goal_key = tmpl["title"].lower()[:80]
        if any(goal_key in eg for eg in existing_goals):
            continue  # already queued

        payload = {
            "source": worker_id,
            "original_prompt": tmpl["description"],
            "normalized_goal": tmpl["title"],
            "task_type": tmpl["task_type"],
            "risk_level": "low",
            "status": "planned",
            "approval_required": False,
            "created_at": _now(),
        }
        result = _post("agent_dispatch_tasks", payload)
        if not result.get("error"):
            created.append(result)

    return created


def claim_idle_task(worker_id: str) -> dict | None:
    """
    Claim the next available improvement task for a worker.
    Returns the task dict or None if nothing available.
    """
    tasks = _get(
        "agent_dispatch_tasks?select=id,normalized_goal,task_type,original_prompt"
        "&status=eq.planned&source=eq.improvement_worker"
        "&approval_required=eq.false&order=created_at.asc&limit=1"
    )
    if not tasks:
        return None

    task = tasks[0]
    task_id = task["id"]

    # Mark as running
    url = _sb_url()
    key = _sb_key()
    if not url or not key:
        return None

    patch = json.dumps({"status": "running", "updated_at": _now()}).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/agent_dispatch_tasks?id=eq.{task_id}",
        data=patch,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        return None

    return task


def is_safe_task(task_type: str) -> bool:
    """Return True if task_type is safe for autonomous execution."""
    return task_type in SAFE_TASK_TYPES


def is_unsafe_task(task_type: str) -> bool:
    """Return True if task_type requires human approval."""
    return task_type in UNSAFE_REQUIRES_APPROVAL


def queue_status() -> dict:
    """Return current improvement queue stats."""
    planned = _get(
        "agent_dispatch_tasks?select=id,task_type,normalized_goal"
        "&status=eq.planned&source=eq.improvement_worker&limit=20"
    )
    running = _get(
        "agent_dispatch_tasks?select=id,task_type"
        "&status=eq.running&source=eq.improvement_worker&limit=10"
    )
    completed = _get(
        "agent_dispatch_tasks?select=id"
        "&status=eq.completed_with_evidence&source=eq.improvement_worker&limit=50"
    )
    return {
        "planned": len(planned),
        "running": len(running),
        "completed_with_evidence": len(completed),
        "planned_tasks": [t.get("normalized_goal","?") for t in planned[:5]],
    }


if __name__ == "__main__":
    print("Seeding improvement tasks...")
    tasks = seed_improvement_tasks(limit=3)
    print(f"Created {len(tasks)} tasks")
    for t in tasks:
        print(f"  - {t.get('normalized_goal','?')} [{t.get('id','?')}]")
    print()
    status = queue_status()
    print(f"Queue status: planned={status['planned']} running={status['running']} done={status['completed_with_evidence']}")
