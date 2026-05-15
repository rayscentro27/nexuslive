from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_CONFIG_PATH = Path(__file__).resolve().parent / "revenue_foundation_config.json"


def load_revenue_foundation_config() -> dict[str, Any]:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_revenue_dashboard_stub() -> dict[str, Any]:
    cfg = load_revenue_foundation_config()
    newsletter = cfg.get("newsletter") or {}
    affiliates = cfg.get("affiliate_offers") or []
    lead_magnets = cfg.get("lead_magnets") or []
    mini_tools = cfg.get("ai_mini_tools") or []
    products = cfg.get("digital_products") or []
    landing = cfg.get("landing_page_experiments") or []
    waitlist = cfg.get("nexus_waitlist") or {}
    return {
        "enabled": True,
        "read_only": True,
        "newsletter": {
            "provider": newsletter.get("provider", "unknown"),
            "name": newsletter.get("name", "Nexus Newsletter"),
            "cadence": newsletter.get("publish_cadence", "weekly"),
            "queued_topics": len(newsletter.get("weekly_content_queue") or []),
            "sponsorship_readiness": (newsletter.get("sponsorship_readiness") or {}).get("status", "placeholder"),
        },
        "affiliate_stack": {
            "total_partners": len(affiliates),
            "planned_partners": len([a for a in affiliates if (a.get("status") or "").lower() == "planned"]),
            "tracking_mode": "placeholders_only",
        },
        "lead_magnets": {
            "total": len(lead_magnets),
            "draft_count": len([m for m in lead_magnets if (m.get("status") or "").lower() in {"draft", "outline", "planned"}]),
        },
        "mini_tools": {
            "total": len(mini_tools),
            "roadmap_count": len([t for t in mini_tools if (t.get("status") or "").lower() == "roadmap"]),
        },
        "digital_products": {
            "total": len(products),
            "outline_count": len([p for p in products if (p.get("status") or "").lower() == "outline"]),
        },
        "waitlist": {
            "status": waitlist.get("status", "planned"),
            "capture_fields": waitlist.get("capture_fields") or [],
        },
        "experiments": {
            "landing_pages": len(landing),
            "recommendation_rules": len(cfg.get("recommendation_rules") or []),
        },
    }


def suggest_revenue_bundle(opportunity_name: str, category: str = "") -> dict[str, str]:
    cfg = load_revenue_foundation_config()
    rules = cfg.get("recommendation_rules") or []
    target = f"{opportunity_name} {category}".lower()
    best: dict[str, Any] | None = None
    score = 0

    for rule in rules:
        keywords = [str(k).lower() for k in (rule.get("keywords") or [])]
        current = sum(1 for k in keywords if k and k in target)
        if current > score:
            score = current
            best = rule

    if not best:
        return {
            "affiliate_partner": "Notion",
            "lead_magnet": "Top 25 AI Tools to Start an Online Business",
            "newsletter_topic": "Tool stack comparisons",
            "mini_tool": "AI Business Idea Generator",
            "landing_page_experiment": "AI Automation CTA",
        }

    return {
        "affiliate_partner": str(best.get("affiliate_partner") or "Notion"),
        "lead_magnet": str(best.get("lead_magnet") or "Top 25 AI Tools to Start an Online Business"),
        "newsletter_topic": str(best.get("newsletter_topic") or "Tool stack comparisons"),
        "mini_tool": str(best.get("mini_tool") or "AI Business Idea Generator"),
        "landing_page_experiment": str(best.get("landing_page_experiment") or "AI Automation CTA"),
    }
