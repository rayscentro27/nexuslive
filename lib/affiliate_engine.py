"""
Affiliate Monetization Engine
================================
Tracks affiliate opportunities, ranks them by ROI potential, and inserts
recommendations into content drafts.

Runs autonomously — no publishing, no billing, no money movement.

Daily quota: 2 monetization opportunities identified/logged.

Usage:
  from lib.affiliate_engine import run_affiliate_audit, get_top_opportunities
  python3 -m lib.affiliate_engine
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# ─── Master opportunity registry ──────────────────────────────────────────────

AFFILIATE_REGISTRY = [
    {
        "name": "Nav.com",
        "category": "business_credit",
        "commission": "$50-100/ref",
        "cookie_days": 30,
        "min_req": "500+ subscribers",
        "url": "https://nav.com/affiliates",
        "roi_score": 92,
        "applied": False,
        "notes": "Business credit monitoring — perfect fit for Nexus audience",
    },
    {
        "name": "TubeBuddy",
        "category": "ai_tools",
        "commission": "$50/ref (recurring)",
        "cookie_days": 30,
        "min_req": "None",
        "url": "https://tubebuddy.com/affiliate",
        "roi_score": 88,
        "applied": False,
        "notes": "YouTube optimization — apply immediately, no minimum",
    },
    {
        "name": "Pictory AI",
        "category": "ai_tools",
        "commission": "$19/ref (recurring 30%)",
        "cookie_days": 90,
        "min_req": "None",
        "url": "https://pictory.ai/affiliates",
        "roi_score": 85,
        "applied": False,
        "notes": "AI video creation — apply immediately",
    },
    {
        "name": "Credit Suite",
        "category": "business_credit",
        "commission": "$50-200/ref",
        "cookie_days": 60,
        "min_req": "Business finance content",
        "url": "https://creditsuite.com/affiliates",
        "roi_score": 90,
        "applied": False,
        "notes": "Business credit building — high ticket",
    },
    {
        "name": "Fundera / Lendio",
        "category": "funding",
        "commission": "$100-500/ref",
        "cookie_days": 45,
        "min_req": "Funding-related content",
        "url": "https://lendio.com/affiliates",
        "roi_score": 94,
        "applied": False,
        "notes": "Business loans referral — highest value per conversion",
    },
    {
        "name": "Jasper AI",
        "category": "ai_tools",
        "commission": "$40/ref (recurring 25%)",
        "cookie_days": 30,
        "min_req": "500+ traffic/month",
        "url": "https://jasper.ai/affiliates",
        "roi_score": 82,
        "applied": False,
        "notes": "AI writing assistant — great for AI content creators",
    },
    {
        "name": "CapCut Business",
        "category": "ai_tools",
        "commission": "$20/ref",
        "cookie_days": 30,
        "min_req": "None",
        "url": "https://capcut.com/partners",
        "roi_score": 78,
        "applied": False,
        "notes": "Video editing — apply now, great for TikTok content tie-in",
    },
    {
        "name": "Incfile / Northwest Registered Agent",
        "category": "business_formation",
        "commission": "$50-150/ref",
        "cookie_days": 45,
        "min_req": "Business formation content",
        "url": "https://northwest.com/affiliates",
        "roi_score": 86,
        "applied": False,
        "notes": "LLC formation — high intent, converts well with credit building content",
    },
    {
        "name": "Dun & Bradstreet (D&B)",
        "category": "business_credit",
        "commission": "Varies by product",
        "cookie_days": 30,
        "min_req": "Business credit audience",
        "url": "https://www.dnb.com/marketing/partner-programs.html",
        "roi_score": 87,
        "applied": False,
        "notes": "DUNS number registration — directly tied to PAYDEX content",
    },
    {
        "name": "Notion / Monday.com",
        "category": "productivity_tools",
        "commission": "20-30% recurring",
        "cookie_days": 90,
        "min_req": "None",
        "url": "https://affiliate.notion.so",
        "roi_score": 75,
        "applied": False,
        "notes": "Business operations tools — fits AI automation content angle",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sb_insert(table: str, payload: dict) -> dict:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )
    if not url or not key:
        return {"error": "supabase_not_configured"}
    import urllib.request
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
            return result[0] if isinstance(result, list) else result
    except Exception as exc:
        return {"error": str(exc)}


def get_top_opportunities(n: int = 5, category: str | None = None) -> list[dict]:
    """Return top N affiliate opportunities sorted by ROI score."""
    filtered = AFFILIATE_REGISTRY
    if category:
        filtered = [a for a in AFFILIATE_REGISTRY if a["category"] == category]
    return sorted(filtered, key=lambda x: x["roi_score"], reverse=True)[:n]


def get_immediately_applicable() -> list[dict]:
    """Return programs that can be applied to right now (no minimum requirements)."""
    return [
        a for a in AFFILIATE_REGISTRY
        if a["min_req"] in ("None", "") and not a.get("applied")
    ]


def generate_affiliate_recommendations() -> list[dict]:
    """Create worker_recommendations for top unapplied programs."""
    top = get_top_opportunities(n=5)
    immediate = get_immediately_applicable()
    created = []

    # Immediate apply recommendations
    for prog in immediate[:2]:
        rec = {
            "worker_id": "affiliate_worker",
            "category": "affiliate",
            "priority": "high",
            "title": f"Apply to {prog['name']} affiliate program",
            "description": (
                f"{prog['name']} ({prog['category']}) — commission: {prog['commission']}. "
                f"No minimum requirement. Apply at: {prog['url']}. "
                f"ROI score: {prog['roi_score']}/100. {prog['notes']}"
            ),
            "action_required": f"Visit {prog['url']} and submit application",
            "evidence": "affiliate_engine.py registry — no minimum requirement confirmed",
            "estimated_value": prog["commission"],
            "status": "open",
            "created_at": _now(),
        }
        result = _sb_insert("worker_recommendations", rec)
        if not result.get("error"):
            created.append(result)

    # Strategic recommendations for high-value programs
    for prog in top[:3]:
        if prog.get("applied"):
            continue
        rec = {
            "worker_id": "affiliate_worker",
            "category": "affiliate",
            "priority": "medium",
            "title": f"Qualify for {prog['name']} — {prog['commission']}",
            "description": (
                f"Target: {prog['name']} | Requirement: {prog['min_req']} | "
                f"Commission: {prog['commission']} | ROI: {prog['roi_score']}/100. "
                f"{prog['notes']}"
            ),
            "action_required": f"Meet requirement '{prog['min_req']}' then apply at {prog['url']}",
            "evidence": "affiliate_engine.py registry",
            "estimated_value": prog["commission"],
            "status": "open",
            "created_at": _now(),
        }
        result = _sb_insert("worker_recommendations", rec)
        if not result.get("error"):
            created.append(result)

    return created


def insert_affiliate_cta_into_content(content_type: str, topic: str) -> str:
    """
    Return an affiliate CTA block to append to content drafts.
    Selects the most relevant affiliate program for the topic.
    """
    topic_lower = topic.lower()
    if any(k in topic_lower for k in ["credit", "paydex", "duns", "d&b", "tradeline"]):
        prog = next((a for a in AFFILIATE_REGISTRY if a["name"] == "Nav.com"), None)
    elif any(k in topic_lower for k in ["funding", "loan", "capital"]):
        prog = next((a for a in AFFILIATE_REGISTRY if "Lendio" in a["name"]), None)
    elif any(k in topic_lower for k in ["youtube", "video", "content"]):
        prog = next((a for a in AFFILIATE_REGISTRY if a["name"] == "TubeBuddy"), None)
    elif any(k in topic_lower for k in ["ai", "automation", "tool"]):
        prog = next((a for a in AFFILIATE_REGISTRY if a["name"] == "Jasper AI"), None)
    elif any(k in topic_lower for k in ["llc", "formation", "business entity"]):
        prog = next((a for a in AFFILIATE_REGISTRY if "Northwest" in a["name"]), None)
    else:
        prog = get_top_opportunities(n=1)[0]

    if not prog:
        return ""

    if content_type == "newsletter":
        return (
            f"\n\n---\n"
            f"**Tool Recommendation:** {prog['name']} — {prog['notes']}  \n"
            f"*Commission disclosure: affiliate link. See {prog['url']}*\n"
        )
    elif content_type in ("youtube_script", "seo_article"):
        return (
            f"\n\n---\n"
            f"**RESOURCE MENTIONED:** {prog['name']}  \n"
            f"Link in description → [AFFILIATE LINK PLACEHOLDER]  \n"
            f"Commission: {prog['commission']}\n"
        )
    return f"\n\n[Affiliate: {prog['name']} — {prog['url']}]"


def run_affiliate_audit() -> dict:
    """Run full affiliate audit — recommend immediate applications + strategic targets."""
    print("[affiliate_engine] Running affiliate monetization audit...")
    top = get_top_opportunities(n=10)
    immediate = get_immediately_applicable()
    recs = generate_affiliate_recommendations()

    print(f"  Registry: {len(AFFILIATE_REGISTRY)} programs")
    print(f"  Immediately applicable: {len(immediate)}")
    print(f"  Recommendations created: {len(recs)}")
    print(f"\n  Top opportunities:")
    for p in top[:5]:
        print(f"    [{p['roi_score']}] {p['name']:30} {p['commission']}")

    # Save audit report
    report_dir = ROOT / "docs" / "content"
    report_dir.mkdir(parents=True, exist_ok=True)
    today_compact = date.today().strftime("%Y%m%d")
    report_path = report_dir / f"{today_compact}_affiliate_audit.md"
    lines = [
        "# Affiliate Monetization Audit",
        f"Generated: {_now()}",
        "",
        f"## Immediately Applicable ({len(immediate)} programs)",
    ]
    for p in immediate:
        lines.append(f"- **{p['name']}** — {p['commission']} | Apply: {p['url']}")
    lines += ["", "## Top 5 by ROI Score", "| Program | Category | Commission | ROI |", "|---------|----------|-----------|-----|"]
    for p in top[:5]:
        lines.append(f"| {p['name']} | {p['category']} | {p['commission']} | {p['roi_score']}/100 |")
    report_path.write_text("\n".join(lines))
    print(f"\n  Report saved: {report_path}")

    return {
        "date": date.today().isoformat(),
        "total_programs": len(AFFILIATE_REGISTRY),
        "immediately_applicable": len(immediate),
        "recommendations_created": len(recs),
        "top_opportunity": top[0]["name"] if top else None,
        "report_path": str(report_path),
    }


if __name__ == "__main__":
    result = run_affiliate_audit()
    print(f"\nAudit complete: {result}")
