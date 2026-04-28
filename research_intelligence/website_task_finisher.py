"""
Website task finisher.

Consumes ready WebsiteBuilder implementation tasks and turns them into
concrete page/copy assets inside the generated site bundle.
"""

from __future__ import annotations

import json
import os
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

from research_intelligence.landing_page_copy_formatter import format_business_copy

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


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


def _website_tasks(project_id: str) -> List[dict]:
    return _sb_get(
        "implementation_tasks"
        "?select=id,project_id,task_order,task_type,title,details,assigned_team,status,metadata,updated_at"
        f"&project_id=eq.{_quote(project_id)}"
        "&assigned_team=eq.WebsiteBuilder"
        "&status=in.(ready,pending,in_progress)"
        "&order=task_order.asc"
    )


def _recommendation(rec_id: str) -> Optional[dict]:
    rows = _sb_get(
        "research_recommendations"
        "?select=id,title,summary,thesis,profitability_path,metadata"
        f"&id=eq.{_quote(rec_id)}&limit=1"
    )
    return rows[0] if rows else None


def _bundle_dir(project: dict) -> Path:
    return Path((project.get("metadata") or {}).get("site_bundle_path"))


def _render_page(title: str, heading: str, intro: str, bullets: List[str], cta: str) -> str:
    bullet_html = "\n".join(f"          <li>{item}</li>" for item in bullets)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main class="page">
      <section class="hero">
        <p class="eyebrow">Generated Website Task Asset</p>
        <h1>{heading}</h1>
        <p class="lede">{intro}</p>
      </section>
      <section class="card">
        <ul>
{bullet_html}
        </ul>
      </section>
      <section class="card">
        <h2>Next Step</h2>
        <p>{cta}</p>
      </section>
    </main>
  </body>
</html>
"""


def _write_asset(project: dict, task: dict, recommendation: dict) -> str:
    base = _bundle_dir(project)
    copy = format_business_copy(recommendation)
    title = task.get("title") or "Website task"
    if task.get("task_order") == 2:
        path = base / "landing-page-copy.md"
        content = "\n".join(
            [
                f"# {copy['headline']}",
                "",
                copy["subheadline"],
                "",
                "## Offer",
                recommendation.get("metadata", {}).get("offer") or "n/a",
                "",
                "## Outcome Bullets",
                "",
                *[f"- {item}" for item in copy["offer_bullets"]],
                "",
                "## CTA",
                "",
                copy["cta_label"],
                copy["cta_support"],
                "",
            ]
        )
    elif task.get("task_order") == 4:
        path = base / "sitemap-outline.md"
        site_plan = base / "site-plan.json"
        content = "\n".join(
            [
                f"# {title}",
                "",
                "## Generated Pages",
                "",
                "- `/` landing page",
                "- `/offer` offer overview",
                "- `/pricing` pricing page",
                "- `/process` workflow/process page",
                "- `/contact` conversion page",
                "",
                f"See also: `{site_plan.name}`",
                "",
            ]
        )
    else:
        path = base / "service-pages.html"
        content = _render_page(
            recommendation.get("title") or "Service Pages",
            "Service scope and delivery model",
            copy["positioning"],
            [
                recommendation.get("metadata", {}).get("offer") or "Focused offer",
                recommendation.get("metadata", {}).get("pricing_model") or "Clear pricing",
                recommendation.get("metadata", {}).get("acquisition_channel") or "Clear acquisition channel",
            ],
            copy["cta_support"],
        )
    path.write_text(content, encoding="utf-8")
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


def finish_once(limit: int = 10) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    projects = _active_projects(limit)
    completed = 0
    outputs: List[str] = []
    for project in projects:
        recommendation = _recommendation(project["recommendation_id"])
        if not recommendation:
            continue
        tasks = _website_tasks(project["id"])
        for task in tasks:
            output_path = _write_asset(project, task, recommendation)
            metadata = dict(task.get("metadata") or {})
            metadata["output_path"] = output_path
            metadata["completed_by_worker"] = "website_task_finisher"
            _patch_task(
                task["id"],
                {
                    "status": "completed",
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            outputs.append(output_path)
            completed += 1
        _maybe_complete_project(project)
    return {
        "projects_found": len(projects),
        "website_tasks_completed": completed,
        "outputs_written": outputs[:10],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(finish_once(limit=args.limit), indent=2))
