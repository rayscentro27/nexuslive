"""
Recommendation review CLI.

Provides a small operator workflow for reviewing `research_recommendations`
without manually patching rows in Supabase.
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

from research_intelligence.approval_handoff_worker import handoff_once
from research_intelligence.business_task_executor import execute_once as business_execute_once
from research_intelligence.site_build_worker import build_once
from research_intelligence.trading_task_executor import execute_once as trading_execute_once
from research_intelligence.website_task_finisher import finish_once as website_finish_once

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


def _require_env() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")


def list_recommendations(limit: int = 20, status: Optional[str] = None, domain: Optional[str] = None) -> List[dict]:
    _require_env()
    parts = [
        "research_recommendations",
        "?select=id,domain,title,score,confidence,recommendation,approval_status,created_at,metadata",
    ]
    if status:
        parts.append(f"&approval_status=eq.{_quote(status)}")
    if domain:
        parts.append(f"&domain=eq.{_quote(domain)}")
    parts.append("&order=created_at.desc")
    parts.append(f"&limit={int(limit)}")
    rows = _sb_get("".join(parts))
    return rows


def get_recommendation(rec_id: str) -> Optional[dict]:
    _require_env()
    rows = _sb_get(
        "research_recommendations"
        "?select=id,domain,category,title,score,confidence,recommendation,approval_status,summary,thesis,execution_plan,profitability_path,backend_handoff,metadata,trace_id,created_at,updated_at"
        f"&id=eq.{_quote(rec_id)}&limit=1"
    )
    return rows[0] if rows else None


def set_approval(rec_id: str, approval_status: str, note: Optional[str] = None) -> dict:
    _require_env()
    rec = get_recommendation(rec_id)
    if not rec:
        raise RuntimeError(f"Recommendation not found: {rec_id}")
    metadata = dict(rec.get("metadata") or {})
    metadata["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    metadata["review_action"] = approval_status
    if note:
        metadata["review_note"] = note
    _sb_patch(
        "research_recommendations",
        f"id=eq.{_quote(rec_id)}",
        {
            "approval_status": approval_status,
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    updated = get_recommendation(rec_id)
    if not updated:
        raise RuntimeError(f"Recommendation disappeared after update: {rec_id}")
    return updated


def run_approved_flow(rec_id: str, note: Optional[str] = None, site_limit: int = 5) -> dict:
    approved = set_approval(rec_id, "approved", note=note)
    handoff = handoff_once(limit=20)
    site = build_once(limit=site_limit)
    business = business_execute_once(limit=site_limit)
    website = website_finish_once(limit=site_limit)
    trading = trading_execute_once(limit=site_limit)
    refreshed = get_recommendation(rec_id)
    return {
        "recommendation": refreshed or approved,
        "handoff_result": handoff,
        "site_result": site,
        "business_task_result": business,
        "website_task_result": website,
        "trading_task_result": trading,
    }


def _render_list(rows: List[dict]) -> str:
    if not rows:
        return "No recommendations found."
    lines = []
    for row in rows:
        lines.append(
            " | ".join(
                [
                    str(row.get("id")),
                    str(row.get("domain")),
                    str(row.get("approval_status")),
                    f"score={row.get('score')}",
                    f"confidence={row.get('confidence')}",
                    str(row.get("title")),
                ]
            )
        )
    return "\n".join(lines)


def _render_detail(rec: dict) -> str:
    metadata = rec.get("metadata") or {}
    sections = [
        f"id: {rec.get('id')}",
        f"title: {rec.get('title')}",
        f"domain: {rec.get('domain')}",
        f"approval_status: {rec.get('approval_status')}",
        f"score: {rec.get('score')}",
        f"confidence: {rec.get('confidence')}",
        f"recommendation: {rec.get('recommendation')}",
        "",
        f"summary: {rec.get('summary')}",
        "",
        f"thesis: {rec.get('thesis')}",
        "",
        "execution_plan:",
    ]
    for item in rec.get("execution_plan") or []:
        sections.append(f"- {item}")
    sections.extend(
        [
            "",
            f"profitability_path: {rec.get('profitability_path')}",
            "",
            "backend_handoff:",
        ]
    )
    for item in rec.get("backend_handoff") or []:
        sections.append(f"- {item}")
    key_metadata = {
        "headline": metadata.get("headline"),
        "subheadline": metadata.get("subheadline"),
        "positioning": metadata.get("positioning"),
        "icp": metadata.get("icp"),
        "offer": metadata.get("offer"),
        "pricing_model": metadata.get("pricing_model"),
        "acquisition_channel": metadata.get("acquisition_channel"),
        "implementation_project_id": metadata.get("implementation_project_id"),
    }
    sections.extend(["", "metadata:"])
    for key, value in key_metadata.items():
        if value:
            sections.append(f"- {key}: {value}")
    return "\n".join(sections)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--status")
    p_list.add_argument("--domain")
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show")
    p_show.add_argument("id")
    p_show.add_argument("--json", action="store_true")

    p_approve = sub.add_parser("approve")
    p_approve.add_argument("id")
    p_approve.add_argument("--note")
    p_approve.add_argument("--json", action="store_true")

    p_reject = sub.add_parser("reject")
    p_reject.add_argument("id")
    p_reject.add_argument("--note")
    p_reject.add_argument("--json", action="store_true")

    p_review = sub.add_parser("mark-review")
    p_review.add_argument("id")
    p_review.add_argument("--note")
    p_review.add_argument("--json", action="store_true")

    p_run = sub.add_parser("run-approved")
    p_run.add_argument("id")
    p_run.add_argument("--note")
    p_run.add_argument("--site-limit", type=int, default=5)
    p_run.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "list":
        rows = list_recommendations(limit=args.limit, status=args.status, domain=args.domain)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(_render_list(rows))
    elif args.command == "show":
        rec = get_recommendation(args.id)
        if not rec:
            raise SystemExit(f"Recommendation not found: {args.id}")
        if args.json:
            print(json.dumps(rec, indent=2))
        else:
            print(_render_detail(rec))
    elif args.command == "approve":
        rec = set_approval(args.id, "approved", note=args.note)
        print(json.dumps(rec, indent=2) if args.json else _render_detail(rec))
    elif args.command == "reject":
        rec = set_approval(args.id, "rejected", note=args.note)
        print(json.dumps(rec, indent=2) if args.json else _render_detail(rec))
    elif args.command == "mark-review":
        rec = set_approval(args.id, "pending", note=args.note)
        print(json.dumps(rec, indent=2) if args.json else _render_detail(rec))
    elif args.command == "run-approved":
        result = run_approved_flow(args.id, note=args.note, site_limit=args.site_limit)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_render_detail(result["recommendation"]))
            print("")
            print(f"handoff_result: {json.dumps(result['handoff_result'])}")
            print(f"site_result: {json.dumps(result['site_result'])}")
