"""
Site build worker.

Consumes queued business implementation projects and scaffolds a local site
bundle under `generated_sites/<slug>/`, then updates implementation project/task
status so backend employees have a concrete starting point.
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

from research_intelligence.landing_page_copy_formatter import format_business_copy

ROOT = Path(__file__).resolve().parent.parent
GENERATED_SITES = ROOT / "generated_sites"

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


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return value or "site-project"


def _queued_projects(limit: int = 10) -> List[dict]:
    path = (
        "implementation_projects"
        "?select=id,recommendation_id,domain,project_type,title,summary,status,metadata,created_at"
        "&domain=eq.business"
        "&project_type=eq.business_buildout"
        "&status=in.(queued,in_progress)"
        "&order=created_at.asc"
        f"&limit={limit}"
    )
    rows = _sb_get(path)
    pending = []
    for row in rows:
        metadata = row.get("metadata") or {}
        if metadata.get("site_bundle_path"):
            continue
        pending.append(row)
    return pending


def _fetch_recommendation(recommendation_id: str) -> Optional[dict]:
    encoded = urllib.parse.quote(str(recommendation_id), safe="")
    rows = _sb_get(
        "research_recommendations"
        "?select=id,title,summary,thesis,execution_plan,profitability_path,backend_handoff,metadata"
        f"&id=eq.{encoded}&limit=1"
    )
    return rows[0] if rows else None


def _fetch_tasks(project_id: str) -> List[dict]:
    encoded = urllib.parse.quote(str(project_id), safe="")
    return _sb_get(
        "implementation_tasks"
        "?select=id,task_order,task_type,title,details,assigned_team,status,metadata"
        f"&project_id=eq.{encoded}&order=task_order.asc"
    )


def _sitemap(rec: dict, tasks: List[dict]) -> List[dict]:
    title = rec.get("title") or "Business"
    niche = ((rec.get("metadata") or {}).get("niche") or "offer").replace("_", " ").title()
    pages = [
        {"slug": "/", "title": f"{title}", "goal": "Primary landing page and conversion CTA"},
        {"slug": "/offer", "title": f"{niche} Offer", "goal": "Explain the service or product clearly"},
        {"slug": "/process", "title": "How It Works", "goal": "Show process and reduce buyer friction"},
        {"slug": "/contact", "title": "Get Started", "goal": "Capture leads and schedule next step"},
    ]
    if any("pricing" in (task.get("title") or "").lower() for task in tasks):
        pages.insert(2, {"slug": "/pricing", "title": "Pricing", "goal": "Package and pricing clarity"})
    return pages


def _content_plan(rec: dict, tasks: List[dict], sitemap: List[dict]) -> Dict[str, List[str]]:
    metadata = rec.get("metadata") or {}
    copy = format_business_copy(rec)
    thesis = rec.get("thesis") or "Clear customer problem, clear offer, clear conversion path."
    headline = copy["headline"]
    subheadline = copy["subheadline"]
    positioning = copy["positioning"] or thesis
    profitability = rec.get("profitability_path") or "Acquire first customers, refine delivery, improve retention and margins."
    proof_points = metadata.get("proof_points") or []
    pain_points = metadata.get("pain_points") or []
    icp = metadata.get("icp")
    offer = metadata.get("offer")
    pricing = metadata.get("pricing_model")
    acquisition = metadata.get("acquisition_channel")
    revenue_model = metadata.get("revenue_model")
    if not pain_points:
        pain_points = copy["pain_bullets"]
    offer_outcomes = copy["offer_bullets"]
    return {
        "headline": [headline],
        "subheadline": [subheadline],
        "positioning": [positioning],
        "core_thesis": [thesis],
        "profitability_path": [profitability],
        "ideal_customer_profile": [icp] if icp else [],
        "who_its_for": [copy["who_its_for"]],
        "offer": [offer] if offer else [],
        "pricing_model": [pricing] if pricing else [],
        "pricing_blurb": [copy["pricing_blurb"]],
        "acquisition_channel": [acquisition] if acquisition else [],
        "proof_points": copy["proof_bullets"] or proof_points[:4],
        "customer_pain_points": pain_points[:4],
        "revenue_model": [copy["revenue_model"] or revenue_model] if (copy["revenue_model"] or revenue_model) else [],
        "offer_outcomes": offer_outcomes,
        "cta_label": [copy["cta_label"]],
        "cta_support": [copy["cta_support"]],
        "page_promises": [page["goal"] for page in sitemap],
    }


def _landing_html(rec: dict, sitemap: List[dict], content_plan: Dict[str, List[str]]) -> str:
    title = rec.get("title") or "Business Launch"
    headline = content_plan.get("headline", [title])[0]
    summary = content_plan.get("subheadline", [rec.get("summary") or "A validated business concept ready for launch."])[0]
    thesis = content_plan.get("positioning", [content_plan["core_thesis"][0]])[0]
    cta = content_plan.get("cta_label", ["Book a Discovery Call"])[0]
    offer_title = sitemap[1]["title"] if len(sitemap) > 1 else "Offer"
    pains = "\n".join(f"          <li>{item}</li>" for item in content_plan["customer_pain_points"][:3])
    outcomes = "\n".join(f"          <li>{item}</li>" for item in content_plan.get("offer_outcomes", [])[:4])
    icp = content_plan.get("ideal_customer_profile", ["Growth-focused operators who need a clearer system."])[0]
    who_its_for = content_plan.get("who_its_for", ["This is built for operators who need a clearer path from demand to revenue."])[0]
    offer = content_plan.get("offer", ["A focused productized service offer."])[0]
    pricing = content_plan.get("pricing_model", ["Fixed setup or monthly retainer pricing."])[0]
    pricing_blurb = content_plan.get("pricing_blurb", ["Start with a clear setup package, then expand into recurring optimization."])[0]
    acquisition = content_plan.get("acquisition_channel", ["Direct outreach and content-led lead generation."])[0]
    revenue_model = content_plan.get("revenue_model", ["Productized services with recurring revenue upside."])[0]
    proof = "\n".join(f"          <li>{item}</li>" for item in content_plan.get("proof_points", [])[:3])
    cta_support = content_plan.get("cta_support", ["Connect this section to your CRM form, scheduler, or outbound lead workflow."])[0]
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
        <p class="eyebrow">Generated Site Scaffold</p>
        <h1>{headline}</h1>
        <p class="lede">{summary}</p>
        <p class="thesis">{thesis}</p>
        <div class="actions">
          <a class="button primary" href="#contact">{cta}</a>
          <a class="button secondary" href="#offer">View Offer</a>
        </div>
      </section>

      <section class="grid two-up" id="offer">
        <article class="card">
          <h2>{offer_title}</h2>
          <p><strong>Ideal customer:</strong> {icp}</p>
          <p>{who_its_for}</p>
          <p><strong>Offer:</strong> {offer}</p>
          <ul>
{outcomes}
          </ul>
        </article>
        <article class="card">
          <h2>Why Buyers Care</h2>
          <ul>
{pains}
          </ul>
        </article>
      </section>

      <section class="card">
        <h2>Commercial Model</h2>
        <p><strong>Pricing:</strong> {pricing}</p>
        <p>{pricing_blurb}</p>
        <p><strong>First acquisition channel:</strong> {acquisition}</p>
        <p><strong>Revenue model:</strong> {revenue_model}</p>
      </section>

      <section class="card">
        <h2>Proof And Positioning</h2>
        <ul>
{proof}
        </ul>
      </section>

      <section class="card">
        <h2>Profitability Path</h2>
        <p>{content_plan["profitability_path"][0]}</p>
      </section>

      <section class="card" id="contact">
        <h2>Next Step</h2>
        <p>{cta_support}</p>
      </section>
    </main>
  </body>
</html>
"""


def _styles_css() -> str:
    return """* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  background: linear-gradient(180deg, #f6f1e8 0%, #efe3d0 100%);
  color: #1f1c18;
}
.page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 20px 64px;
}
.hero {
  padding: 48px 0 32px;
}
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  color: #7b5b35;
}
h1, h2 {
  font-weight: 600;
  line-height: 1.1;
}
h1 {
  font-size: clamp(2.4rem, 6vw, 4.8rem);
  max-width: 12ch;
  margin: 0.2em 0;
}
.lede, .thesis, p, li {
  font-size: 1.05rem;
  line-height: 1.6;
}
.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 24px;
}
.button {
  display: inline-block;
  padding: 14px 18px;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
}
.primary {
  background: #1f1c18;
  color: #f6f1e8;
}
.secondary {
  background: transparent;
  color: #1f1c18;
  border: 1px solid #1f1c18;
}
.grid {
  display: grid;
  gap: 20px;
}
.two-up {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}
.card {
  background: rgba(255,255,255,0.7);
  border: 1px solid rgba(31,28,24,0.08);
  border-radius: 24px;
  padding: 24px;
  margin-top: 20px;
  box-shadow: 0 12px 40px rgba(31,28,24,0.06);
}
ul {
  padding-left: 20px;
}
"""


def _readme(rec: dict, project: dict, tasks: List[dict]) -> str:
    return f"""# {rec.get('title') or project.get('title')}

Generated from approved research recommendation `{rec.get('id')}`.

## Project

- Domain: {project.get('domain')}
- Type: {project.get('project_type')}
- Summary: {project.get('summary') or 'n/a'}

## Thesis

{rec.get('thesis') or 'n/a'}

## Profitability Path

{rec.get('profitability_path') or 'n/a'}

## Tasks

""" + "\n".join(f"- [{task.get('assigned_team')}] {task.get('title')}" for task in tasks)


def _write_bundle(project: dict, rec: dict, tasks: List[dict]) -> str:
    GENERATED_SITES.mkdir(parents=True, exist_ok=True)
    slug = _slugify(project.get("title") or rec.get("title") or str(project.get("id")))
    project_dir = GENERATED_SITES / slug
    project_dir.mkdir(parents=True, exist_ok=True)

    sitemap = _sitemap(rec, tasks)
    content_plan = _content_plan(rec, tasks, sitemap)

    (project_dir / "site-plan.json").write_text(json.dumps({
        "project": project,
        "recommendation": rec,
        "sitemap": sitemap,
        "content_plan": content_plan,
    }, indent=2), encoding="utf-8")
    (project_dir / "index.html").write_text(_landing_html(rec, sitemap, content_plan), encoding="utf-8")
    (project_dir / "styles.css").write_text(_styles_css(), encoding="utf-8")
    (project_dir / "README.md").write_text(_readme(rec, project, tasks), encoding="utf-8")

    return str(project_dir)


def _patch_project(project_id: str, data: dict) -> None:
    query = f"id=eq.{urllib.parse.quote(str(project_id), safe='')}"
    _sb_patch("implementation_projects", query, data)


def _patch_task(task_id: str, data: dict) -> None:
    query = f"id=eq.{urllib.parse.quote(str(task_id), safe='')}"
    _sb_patch("implementation_tasks", query, data)


def build_once(limit: int = 5) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    built = 0
    projects = _queued_projects(limit)
    for project in projects:
        rec = _fetch_recommendation(project["recommendation_id"])
        if not rec:
            continue
        tasks = _fetch_tasks(project["id"])
        bundle_path = _write_bundle(project, rec, tasks)
        metadata = dict(project.get("metadata") or {})
        metadata.update({
            "site_bundle_path": bundle_path,
            "site_generated_at": datetime.now(timezone.utc).isoformat(),
        })
        _patch_project(project["id"], {
            "status": "in_progress",
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        for task in tasks:
            if task.get("assigned_team") == "WebsiteBuilder":
                _patch_task(task["id"], {
                    "status": "ready",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
        built += 1
    return {"projects_found": len(projects), "built": built}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(build_once(limit=args.limit), indent=2))
