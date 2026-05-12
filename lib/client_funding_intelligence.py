from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import os

from lib.hermes_knowledge_brain import build_source_aware_context_pack, get_top_ranked_knowledge


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _safe_select(path: str, timeout: int = 8) -> list[dict[str, Any]]:
    try:
        from scripts.prelaunch_utils import rest_select

        return rest_select(path, timeout=timeout) or []
    except Exception:
        return []


def _missing_data_flags() -> list[str]:
    checks = {
        "business_profile": "business profile details",
        "credit_profile": "credit profile",
        "bank_statements": "bank statements",
        "entity_docs": "entity setup docs",
    }
    rows = _safe_select("workflow_outputs?select=summary,workflow_type,status,created_at&order=created_at.desc&limit=80")
    text = " ".join(str(r.get("summary") or "").lower() for r in rows)
    missing = []
    for key, label in checks.items():
        if key not in text:
            missing.append(label)
    return missing


def _capital_ladder_summary() -> list[dict[str, Any]]:
    return [
        {"stage": 1, "name": "credit stabilization", "goal": "improve profile consistency"},
        {"stage": 2, "name": "starter capital", "goal": "secure small revolving lines"},
        {"stage": 3, "name": "growth capital", "goal": "expand limits with stronger docs"},
    ]


def get_funding_blockers() -> list[str]:
    summary = build_client_funding_intelligence_summary(include_source_context=False)
    return list(summary.get("funding_blockers") or [])


def get_credit_readiness_summary() -> dict[str, Any]:
    summary = build_client_funding_intelligence_summary(include_source_context=False)
    return dict(summary.get("credit_readiness_summary") or {})


def get_business_setup_readiness_summary() -> dict[str, Any]:
    summary = build_client_funding_intelligence_summary(include_source_context=False)
    return dict(summary.get("business_setup_readiness_summary") or {})


def recommend_next_funding_action() -> str:
    summary = build_client_funding_intelligence_summary(include_source_context=False)
    return str(summary.get("next_best_funding_action") or "Review readiness blockers and collect missing data.")


def build_client_funding_summary() -> dict[str, Any]:
    return build_client_funding_intelligence_summary(include_source_context=False)


def build_client_funding_intelligence_summary(include_source_context: bool = False) -> dict[str, Any]:
    funding = get_top_ranked_knowledge("funding", limit=6)
    credit = get_top_ranked_knowledge("credit", limit=6)
    business_setup = get_top_ranked_knowledge("business_setup", limit=5)
    grants = get_top_ranked_knowledge("grants", limit=5)
    missing = _missing_data_flags()
    blockers = [
        "Missing key readiness documents." if missing else "No critical document blockers detected.",
        "Credit readiness requires consistency checks." if len(credit) == 0 else "Credit insights available.",
    ]
    next_action = "Compile missing readiness items and review the top ranked funding recommendation."
    out = {
        "timestamp": _now(),
        "enabled": _flag("CLIENT_FUNDING_INTELLIGENCE_ENABLED", "true"),
        "review_only": _flag("FUNDING_INTELLIGENCE_REVIEW_ONLY", "true"),
        "actions_require_approval": _flag("FUNDING_ACTIONS_REQUIRE_APPROVAL", "true"),
        "funding_readiness_summary": {
            "top_recommendations": funding[:3],
            "confidence": "medium" if funding else "low",
        },
        "credit_readiness_summary": {
            "top_recommendations": credit[:3],
            "confidence": "medium" if credit else "low",
        },
        "business_setup_readiness_summary": {
            "top_recommendations": business_setup[:3],
            "confidence": "medium" if business_setup else "low",
        },
        "grant_readiness_summary": {
            "top_recommendations": grants[:3],
            "confidence": "medium" if grants else "low",
        },
        "missing_data": missing,
        "funding_blockers": blockers,
        "next_best_funding_action": next_action,
        "capital_ladder_recommendation": _capital_ladder_summary(),
    }
    if include_source_context:
        out["source_aware_context"] = {
            "funding": build_source_aware_context_pack("funding", limit=5),
            "credit": build_source_aware_context_pack("credit", limit=5),
        }
    else:
        out["source_aware_context"] = {"funding": {}, "credit": {}}
    return out
