from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import os

from lib.hermes_knowledge_brain import build_source_aware_context_pack, get_top_ranked_knowledge


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def build_opportunity_intelligence_summary(include_source_context: bool = False) -> dict[str, Any]:
    grants = get_top_ranked_knowledge("grants", limit=6)
    business = get_top_ranked_knowledge("business_setup", limit=4)
    operations = get_top_ranked_knowledge("operations", limit=4)
    top = grants[:2] + business[:1] + operations[:1]
    blockers = []
    if not grants:
        blockers.append("No fresh grant intelligence signals detected.")
    if not business:
        blockers.append("Business opportunity qualification data is sparse.")
    next_action = "Review top opportunity candidates and collect missing application prerequisites."
    out = {
        "timestamp": _now(),
        "enabled": _flag("OPPORTUNITY_INTELLIGENCE_ENABLED", "true"),
        "review_only": _flag("OPPORTUNITY_REVIEW_ONLY", "true"),
        "actions_require_approval": _flag("OPPORTUNITY_ACTIONS_REQUIRE_APPROVAL", "true"),
        "grant_opportunity_summary": grants[:3],
        "business_opportunity_summary": business[:3],
        "opportunity_fit_score": "medium" if top else "low",
        "effort_vs_reward_summary": "Prioritize medium-effort/high-fit opportunities first.",
        "urgency_expiration_awareness": "Monitor upcoming deadlines and first-window eligibility.",
        "application_readiness_blockers": blockers,
        "opportunity_next_action": next_action,
        "categories": [
            "grants",
            "government contracts",
            "business opportunities",
            "online income opportunities",
            "local opportunities",
            "partnerships",
            "vendor/client opportunities",
        ],
        "source_aware_context": {},
    }
    if include_source_context:
        out["source_aware_context"] = build_source_aware_context_pack("grants", limit=5)
    return out


def summarize_grant_opportunities() -> list[dict[str, Any]]:
    return list((build_opportunity_intelligence_summary().get("grant_opportunity_summary") or []))


def summarize_business_opportunities() -> list[dict[str, Any]]:
    return list((build_opportunity_intelligence_summary().get("business_opportunity_summary") or []))


def score_opportunity_fit() -> str:
    return str(build_opportunity_intelligence_summary().get("opportunity_fit_score") or "low")


def recommend_opportunity_next_action() -> str:
    return str(build_opportunity_intelligence_summary().get("opportunity_next_action") or "Review shortlist and readiness blockers.")


def build_opportunity_summary() -> dict[str, Any]:
    return build_opportunity_intelligence_summary()
