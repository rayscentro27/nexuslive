"""
Approval -> execution handoff worker.

Polls approved `research_recommendations` and creates:
  - implementation_projects
  - implementation_tasks
  - workflow_outputs summary row

This gives backend employees a structured queue once the operator approves
an opportunity or trading recommendation.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
POLL_SECONDS = int(os.getenv("RESEARCH_APPROVAL_POLL_SECONDS", "120"))


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


def _sb_post(table: str, rows: List[dict], prefer: str = "return=representation") -> List[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}",
        data=json.dumps(rows).encode(),
        headers=_headers(prefer),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_post_safe(table: str, rows: List[dict], prefer: str = "return=representation") -> tuple[bool, str]:
    try:
        _sb_post(table, rows, prefer=prefer)
        return True, ""
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode()
        except Exception:
            detail = str(exc)
        return False, detail


def _sb_patch(table: str, query: str, data: dict) -> None:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{query}",
        data=json.dumps(data).encode(),
        headers=_headers("return=minimal"),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20):
        pass


def _patch_project(project_id: str, data: dict) -> None:
    query = f"id=eq.{urllib.parse.quote(str(project_id), safe='')}"
    _sb_patch("implementation_projects", query, data)


def _deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _team_for_text(text: str, domain: str) -> str:
    t = (text or "").lower()
    if domain == "trading":
        if any(k in t for k in ("paper", "risk", "replay", "trade")):
            return "TradingEngine"
        return "ResearchDesk"
    if any(k in t for k in ("website", "landing page", "page", "copy", "sitemap", "brand")):
        return "WebsiteBuilder"
    if any(k in t for k in ("crm", "automation", "lead", "email", "analytics")):
        return "OpsAutomation"
    if any(k in t for k in ("offer", "pricing", "product", "service")):
        return "OpportunityWorker"
    return "BackendEmployees"


def _project_type(rec: dict) -> str:
    if rec.get("domain") == "trading":
        return "trading_execution"
    return "business_buildout"


def _workflow_output(rec: dict, project_id: str, workflow_id: str, tasks: List[dict]) -> dict:
    domain = rec.get("domain")
    title = rec.get("title") or "Untitled recommendation"
    summary = rec.get("summary") or f"Approved {domain} recommendation ready for execution."
    primary_action = "Build launch assets" if domain == "business" else "Validate and promote to paper path"
    return {
        "workflow_id": workflow_id,
        "workflow_type": "research_recommendation_handoff",
        "tenant_id": None,
        "client_id": None,
        "subject_type": domain,
        "subject_id": str(rec.get("id")),
        "status": "completed",
        "summary": summary,
        "primary_action_key": "execute_approved_recommendation",
        "primary_action_title": primary_action,
        "primary_action_description": f"{title} has been converted into implementation tasks for backend workers.",
        "priority": "high",
        "score": int(float(rec.get("score") or 0)) if rec.get("score") is not None else None,
        "readiness_level": "ready",
        "blockers": [],
        "strengths": [rec.get("thesis")] if rec.get("thesis") else [],
        "suggested_tasks": [task["title"] for task in tasks[:6]],
        "source_job_id": None,
        "raw_output": {
            "recommendation_id": rec.get("id"),
            "implementation_project_id": project_id,
            "domain": domain,
            "task_count": len(tasks),
        },
    }


def _task_rows(project_id: str, rec: dict) -> List[dict]:
    plan = rec.get("execution_plan") or []
    handoff = rec.get("backend_handoff") or []
    items = []
    for idx, text in enumerate(plan + handoff):
        if not text:
            continue
        items.append(
            {
                "id": _deterministic_uuid(f"implementation-task:{project_id}:{idx}:{text}"),
                "project_id": project_id,
                "task_order": idx,
                "task_type": "execution_plan" if idx < len(plan) else "backend_handoff",
                "title": str(text)[:180],
                "details": str(text),
                "assigned_team": _team_for_text(str(text), rec.get("domain")),
                "status": "pending",
                "metadata": {
                    "recommendation_id": rec.get("id"),
                    "domain": rec.get("domain"),
                },
            }
        )
    return items


def _approved_rows(limit: int = 20) -> List[dict]:
    path = (
        "research_recommendations"
        "?select=id,source_table,source_id,domain,category,title,score,confidence,recommendation,summary,thesis,execution_plan,profitability_path,backend_handoff,approval_status,metadata,trace_id,created_at"
        "&approval_status=eq.approved"
        "&order=created_at.asc"
        f"&limit={limit}"
    )
    rows = _sb_get(path)
    pending = []
    for row in rows:
        metadata = row.get("metadata") or {}
        if metadata.get("handoff_created"):
            continue
        pending.append(row)
    return pending


def _create_project(rec: dict) -> str:
    project_id = _deterministic_uuid(f"implementation-project:{rec['id']}")
    workflow_id = _deterministic_uuid(f"workflow-output:{rec['id']}")
    existing = _sb_get(
        "implementation_projects"
        f"?recommendation_id=eq.{urllib.parse.quote(str(rec['id']), safe='')}&select=id&limit=1"
    )
    if existing:
        return existing[0]["id"]
    project = {
        "id": project_id,
        "recommendation_id": rec["id"],
        "domain": rec["domain"],
        "project_type": _project_type(rec),
        "title": rec["title"],
        "summary": rec.get("summary"),
        "status": "queued",
        "owner_hint": _team_for_text(rec.get("title"), rec.get("domain")),
        "source_table": rec.get("source_table"),
        "source_id": rec.get("source_id"),
        "workflow_id": workflow_id,
        "metadata": {
            "recommendation": rec.get("recommendation"),
            "profitability_path": rec.get("profitability_path"),
            "trace_id": rec.get("trace_id"),
        },
    }
    try:
        _sb_post("implementation_projects", [project])
    except urllib.error.HTTPError as exc:
        if exc.code != 409:
            raise
        existing = _sb_get(
            "implementation_projects"
            f"?recommendation_id=eq.{urllib.parse.quote(str(rec['id']), safe='')}&select=id&limit=1"
        )
        if existing:
            return existing[0]["id"]
        raise
    return project_id


def _mark_handed_off(rec: dict, project_id: str) -> None:
    metadata = dict(rec.get("metadata") or {})
    metadata.update(
        {
            "handoff_created": True,
            "implementation_project_id": project_id,
            "handoff_created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    query = f"id=eq.{urllib.parse.quote(str(rec['id']), safe='')}"
    _sb_patch(
        "research_recommendations",
        query,
        {
            "approval_status": "executing",
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def _mark_project_handoff_warning(project_id: str, warning: str) -> None:
    existing = _sb_get(
        "implementation_projects"
        f"?id=eq.{urllib.parse.quote(str(project_id), safe='')}&select=metadata&limit=1"
    )
    metadata = dict((existing[0].get("metadata") if existing else {}) or {})
    metadata["workflow_output_warning"] = warning[:500]
    _patch_project(
        project_id,
        {
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def handoff_once(limit: int = 20) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    rows = _approved_rows(limit)
    handed_off = 0
    for rec in rows:
        project_id = _create_project(rec)
        tasks = _task_rows(project_id, rec)
        existing_tasks = _sb_get(
            "implementation_tasks"
            f"?project_id=eq.{urllib.parse.quote(str(project_id), safe='')}&select=id&limit=1"
        )
        if tasks and not existing_tasks:
            _sb_post("implementation_tasks", tasks)
        workflow_id = _deterministic_uuid(f"workflow-output:{rec['id']}")
        ok, detail = _sb_post_safe("workflow_outputs", [_workflow_output(rec, project_id, workflow_id, tasks)])
        if not ok:
            _mark_project_handoff_warning(project_id, detail)
        _mark_handed_off(rec, project_id)
        handed_off += 1
    return {"approved_found": len(rows), "handed_off": handed_off}


def main_loop() -> None:
    while True:
        result = handoff_once()
        print(json.dumps(result))
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.once:
        print(json.dumps(handoff_once(limit=args.limit), indent=2))
    else:
        main_loop()
