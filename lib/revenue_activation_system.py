from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .nexus_youtube_ops import recommend_revenue_tieins


ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
PLAN_FILE = ROOT / "revenue_engine" / "activation_30_day_plan.json"
LEARNED_FILE = STATE_DIR / "nexus_daily_learnings.json"


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


def load_activation_plan() -> dict[str, Any]:
    return _read_json(PLAN_FILE, {"weeks": [], "ctas": {}, "lead_magnets": []})


def content_pipeline_status() -> dict[str, Any]:
    plan = load_activation_plan()
    weeks = plan.get("weeks") or []
    total = len(weeks)
    active = len([w for w in weeks if str(w.get("status") or "") == "active"])
    return {
        "pipeline": "content -> lead magnet -> newsletter -> onboarding -> conversion",
        "weeks_total": total,
        "weeks_active": active,
        "next_action": (weeks[0].get("focus") if weeks else "Define week 1 activation focus"),
    }


def lead_magnet_catalog() -> list[dict[str, Any]]:
    return load_activation_plan().get("lead_magnets") or []


def intelligence_brief_template() -> dict[str, Any]:
    return {
        "title": "Nexus Intelligence Brief",
        "sections": [
            "Funding opportunities",
            "Grant watch",
            "AI tools and automation discoveries",
            "Business opportunities",
            "Operational lessons",
            "Trading research (demo-only)",
        ],
        "cta": "Join Nexus and apply today’s checklist in your business.",
    }


def business_audit(payload: dict[str, Any]) -> dict[str, Any]:
    gaps = []
    if not payload.get("business_setup_complete"):
        gaps.append("business setup incomplete")
    if float(payload.get("credit_utilization") or 100) > 35:
        gaps.append("credit utilization too high")
    if not payload.get("automation_stack"):
        gaps.append("automation stack missing")
    if not payload.get("newsletter_active"):
        gaps.append("newsletter inactive")

    score = max(0, 100 - (len(gaps) * 18))
    return {
        "readiness_score": score,
        "gaps": gaps,
        "improvement_roadmap": [
            "Resolve top 2 readiness gaps this week",
            "Publish one content asset with lead magnet CTA",
            "Run one bounded conversion experiment",
        ],
        "recommended_actions": [
            "Activate lead capture flow",
            "Improve CTA clarity",
            "Assign one follow-up task to AI workforce",
        ],
        "lead_magnet_recommendation": "30-Day Fundability Guide",
    }


def daily_content_suggestions() -> dict[str, Any]:
    pillars = [
        "business_funding",
        "business_credit",
        "ai_automation",
        "grants",
        "business_opportunities",
        "nexus_build_journey",
        "trading_education_demo_only",
    ]
    picks = pillars[:4]
    return {
        "youtube_ideas": [f"{p.replace('_', ' ').title()} breakdown" for p in picks],
        "shorts_hooks": [
            "Most founders miss this one readiness step.",
            "Do this before applying for funding.",
            "One automation that saves hours weekly.",
        ],
        "x_posts": ["Today’s Nexus insight: stability first, then growth loops."],
        "newsletter_snippet": "This week’s playbook focuses on converting attention into qualified leads.",
        "cta": "Download the checklist and join Nexus updates.",
    }


def affiliate_revenue_map(pillar: str) -> dict[str, Any]:
    tiein = recommend_revenue_tieins(pillar)
    return {
        "pillar": pillar,
        "affiliate_tieins": tiein.get("affiliate_recommendation") or [],
        "cta": f"Start with {tiein.get('lead_magnet')} and apply it this week.",
        "nexus_module": tiein.get("nexus_module_tie_in"),
    }


def daily_learnings_summary() -> dict[str, Any]:
    rows = _read_json(LEARNED_FILE, [])
    if not rows:
        rows = [
            {"created_at": _now(), "category": "operations", "lesson": "Stability-first prioritization improves conversion readiness."}
        ]
        _write_json(LEARNED_FILE, rows)
    return {
        "count": len(rows),
        "latest": rows[-5:],
    }


def travel_mobile_summary() -> dict[str, Any]:
    pipeline = content_pipeline_status()
    return {
        "quick_view": {
            "pipeline_next_action": pipeline.get("next_action"),
            "content_focus_today": "Lead magnet CTA + newsletter bridge",
            "revenue_focus_today": "Audience -> lead capture -> follow-up",
        },
        "mobile_operator_hint": "Ask Hermes: 'How do we make money this week?' and 'What content should we create?'",
    }


def today_in_nexus_summary() -> dict[str, Any]:
    """Recurring daily digest used by Hermes, dashboard, and newsletter."""
    pipeline = content_pipeline_status()
    learned = daily_learnings_summary()
    content = daily_content_suggestions()
    return {
        "headline": "Today in Nexus",
        "sections": {
            "opportunities_discovered": [
                "AI service offers with low startup cost and affiliate tie-ins",
                "Funding-readiness advisory as a productized offer",
            ],
            "grants_and_funding_watch": [
                "Track grant readiness checklist usage and follow-up conversion",
                "Promote fundability guide to newsletter pipeline",
            ],
            "ai_lessons": [
                "Stability-first sequencing improves execution quality",
                "Single flagship CTA outperforms split calls to action",
            ],
            "roadmap_progress": {
                "weeks_total": pipeline.get("weeks_total", 0),
                "weeks_active": pipeline.get("weeks_active", 0),
                "next_focus": pipeline.get("next_action"),
            },
            "trading_intelligence": "Demo-only research mode remains active; risk-first posture preserved.",
            "operational_health": "No live execution; bounded automation only.",
            "content_ideas": (content.get("youtube_ideas") or [])[:3],
            "workforce_office_status": "Coordination active across Hermes, OpenCode, and Claude Code task lanes.",
        },
        "newsletter_ready": {
            "subject": "Today in Nexus: Revenue Loops, Opportunities, and Daily Intelligence",
            "intro": "Here is your daily Nexus operating brief with what to ship next.",
            "cta": "Reply with your top priority and let Hermes assign the next action.",
        },
        "latest_lessons": (learned.get("latest") or [])[-3:],
    }


def flagship_lead_magnet() -> dict[str, Any]:
    """Primary lead magnet package for onboarding and conversion flow."""
    return {
        "name": "Business Funding Readiness Blueprint",
        "components": [
            "funding readiness checklist",
            "readiness score rubric",
            "30-day funding roadmap",
            "ai recommendations by risk profile",
            "cta bridge into Nexus onboarding",
            "newsletter follow-up sequence",
            "affiliate recommendation slots",
        ],
        "primary_cta": "Get your readiness score and 30-day roadmap",
        "follow_up_cta": "Book the AI Business Audit to close top blockers",
    }


def ai_employee_personality_profiles() -> list[dict[str, str]]:
    return [
        {"name": "Hermes", "domain": "operations coordinator", "style": "decisive, concise, priority-first"},
        {"name": "Sage", "domain": "funding and grants strategist", "style": "analytical, risk-aware, practical"},
        {"name": "Vera", "domain": "conversion and onboarding", "style": "clear, empathetic, action-oriented"},
        {"name": "Rex", "domain": "workforce dispatch and execution", "style": "urgent, structured, accountability-driven"},
        {"name": "Aria", "domain": "research synthesis", "style": "evidence-based, neutral, summary-focused"},
        {"name": "Nova", "domain": "opportunity intelligence", "style": "curious, comparative, score-driven"},
        {"name": "Mira", "domain": "content engine", "style": "creative, platform-aware, conversion-minded"},
        {"name": "Orion", "domain": "trading research lab", "style": "disciplined, no-hype, risk-first"},
    ]


def opportunity_hall_of_fame() -> dict[str, Any]:
    return {
        "statuses": ["new", "testing", "promising", "hall_of_fame", "archived"],
        "ranking_dimensions": [
            "traction",
            "revenue_potential",
            "automation_potential",
            "scalability",
            "startup_cost",
            "execution_difficulty",
            "affiliate_fit",
            "audience_fit",
        ],
        "current_focus": "Promote only opportunities that show traction + repeatable execution.",
    }


def strategy_hall_of_fame_refinement() -> dict[str, Any]:
    return {
        "dimensions": [
            "consistency",
            "drawdown",
            "volatility_fit",
            "market_fit",
            "rr_profile",
            "fakeout_resistance",
            "session_fit",
            "strategy_confidence",
        ],
        "gating_rule": "Only demo-validated strategies with controlled drawdown can be promoted.",
        "safety_label": "DEMO / PAPER TRADING ONLY",
    }


def operational_trust_snapshot() -> dict[str, Any]:
    return {
        "telegram_spam_guard": "manual-only summaries, default deny broadcast",
        "automation_boundaries": "no recursive loops, bounded run scopes",
        "trading_safety": {
            "NEXUS_DRY_RUN": True,
            "REAL_MONEY_TRADING": False,
            "LIVE_TRADING": False,
            "TRADING_LIVE_EXECUTION_ENABLED": False,
        },
        "confidence": "high when scheduler and dispatch queues remain within expected bounds",
    }
