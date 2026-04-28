"""
Business task executor.

Consumes business implementation tasks and turns them into local deliverable
documents inside the generated site bundle so the workflow advances beyond
planning/scaffolding.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

SUPPORTED_TEAMS = {"OpportunityWorker", "OpsAutomation", "BackendEmployees"}


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_patch(table: str, query: str, data: dict) -> None:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{query}",
        data=json.dumps(data).encode(),
        headers=_headers("return=minimal"),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20):
        pass


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return value or "task"


def _active_projects(limit: int = 10) -> List[dict]:
    rows = _sb_get(
        "implementation_projects"
        "?select=id,recommendation_id,title,status,metadata,updated_at"
        "&domain=eq.business"
        "&status=in.(queued,in_progress)"
        "&order=created_at.asc"
        f"&limit={limit}"
    )
    return [row for row in rows if (row.get("metadata") or {}).get("site_bundle_path")]


def _project_tasks(project_id: str) -> List[dict]:
    return _sb_get(
        "implementation_tasks"
        "?select=id,project_id,task_order,task_type,title,details,assigned_team,status,metadata,updated_at"
        f"&project_id=eq.{_quote(project_id)}"
        "&status=in.(pending,ready,in_progress)"
        "&order=task_order.asc"
    )


def _recommendation(rec_id: str) -> Optional[dict]:
    rows = _sb_get(
        "research_recommendations"
        "?select=id,title,summary,thesis,profitability_path,metadata"
        f"&id=eq.{_quote(rec_id)}&limit=1"
    )
    return rows[0] if rows else None


def _deliverable_path(project: dict, task: dict) -> Path:
    base = Path((project.get("metadata") or {}).get("site_bundle_path"))
    output_dir = base / "task_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{task.get('task_order', 0):02d}-{_slug(task.get('assigned_team'))}-{_slug(task.get('title'))}.md"
    return output_dir / filename


def _task_sections(task: dict, recommendation: dict) -> List[str]:
    metadata = recommendation.get("metadata") or {}
    return [
        f"# {task.get('title')}",
        "",
        f"Assigned team: {task.get('assigned_team')}",
        f"Task type: {task.get('task_type')}",
        "",
        "## Recommendation Context",
        "",
        f"- Title: {recommendation.get('title')}",
        f"- Headline: {metadata.get('headline') or recommendation.get('title')}",
        f"- ICP: {metadata.get('icp') or 'n/a'}",
        f"- Offer: {metadata.get('offer') or 'n/a'}",
        f"- Pricing: {metadata.get('pricing_model') or 'n/a'}",
        f"- Acquisition: {metadata.get('acquisition_channel') or 'n/a'}",
        "",
        "## Task Brief",
        "",
        task.get("details") or task.get("title") or "No details provided.",
        "",
        "## Suggested Deliverable",
        "",
    ]


def _deliverable_body(task: dict, recommendation: dict) -> str:
    sections = _task_sections(task, recommendation)
    team = task.get("assigned_team")
    metadata = recommendation.get("metadata") or {}
    if team == "OpportunityWorker":
        sections.extend(
            [
                "1. Offer summary",
                f"   {metadata.get('offer') or 'Define the core offer and result.'}",
                "2. Packaging notes",
                "   Outline scope, delivery boundaries, and what is included in the first version.",
                "3. Pricing hypothesis",
                f"   {metadata.get('pricing_model') or 'Draft a simple setup + recurring pricing model.'}",
                "4. Validation plan",
                "   List 5-10 prospect questions to validate pain, urgency, and willingness to pay.",
            ]
        )
    elif team == "OpsAutomation":
        sections.extend(
            [
                "1. CRM workflow recommendation",
                "   Capture lead, assign status, send immediate response, and schedule follow-up reminders.",
                "2. Automation checkpoints",
                "   Add lead source tracking, booked-call conversion, and stale-lead alerts.",
                "3. System requirements",
                "   Note form capture, pipeline stages, notifications, and analytics needs.",
                "4. Launch checklist",
                "   Confirm forms, automations, reporting, and fallback manual process.",
            ]
        )
    else:
        sections.extend(
            [
                "1. Build notes",
                "   Summarize what the backend team needs to support this project.",
                "2. Dependencies",
                "   Note any required forms, routes, assets, or integrations.",
                "3. Handoff checklist",
                "   Confirm the generated site bundle, task outputs, and next owner.",
            ]
        )
    sections.extend(
        [
            "",
            "## Profitability Path",
            "",
            recommendation.get("profitability_path") or "n/a",
            "",
            "## Updated At",
            "",
            datetime.now(timezone.utc).isoformat(),
            "",
        ]
    )
    return "\n".join(sections)


def _write_deliverable(project: dict, task: dict, recommendation: dict) -> str:
    path = _deliverable_path(project, task)
    path.write_text(_deliverable_body(task, recommendation), encoding="utf-8")
    return str(path)


def _patch_task(task_id: str, data: dict) -> None:
    _sb_patch("implementation_tasks", f"id=eq.{_quote(task_id)}", data)


def _maybe_complete_project(project: dict) -> None:
    project_id = project["id"]
    remaining = _sb_get(
        "implementation_tasks"
        "?select=id,status"
        f"&project_id=eq.{_quote(project_id)}"
        "&status=in.(pending,ready,in_progress,blocked)"
        "&limit=1"
    )
    if remaining:
        return
    metadata = dict(project.get("metadata") or {})
    metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
    _sb_patch(
        "implementation_projects",
        f"id=eq.{_quote(project_id)}",
        {
            "status": "completed",
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def execute_once(limit: int = 10) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    projects = _active_projects(limit)
    completed = 0
    written: List[str] = []
    for project in projects:
        recommendation = _recommendation(project["recommendation_id"])
        if not recommendation:
            continue
        tasks = _project_tasks(project["id"])
        for task in tasks:
            if task.get("assigned_team") not in SUPPORTED_TEAMS:
                continue
            path = _write_deliverable(project, task, recommendation)
            metadata = dict(task.get("metadata") or {})
            metadata["output_path"] = path
            metadata["completed_by_worker"] = "business_task_executor"
            _patch_task(
                task["id"],
                {
                    "status": "completed",
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            written.append(path)
            completed += 1
        _maybe_complete_project(project)
    return {
        "projects_found": len(projects),
        "tasks_completed": completed,
        "outputs_written": written[:10],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(execute_once(limit=args.limit), indent=2))
