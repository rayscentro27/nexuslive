from __future__ import annotations

from typing import Any

from funding_engine.approval_scoring import score_approval_recommendation
from funding_engine.constants import DISCLAIMER
from funding_engine.relationship_scoring import recommend_relationship_prep, score_relationship

TIER_1_PRODUCT_TYPES = {
    "business_credit_card",
    "credit_union_business_credit_card",
    "starter_tradeline",
    "banking_relationship_action",
}

TIER_2_PRODUCT_TYPES = {
    "credit_union_loc",
    "sba_microloan",
    "working_capital_loan",
    "credit_union_term_loan",
    "relationship_based_lending",
}


def _matches_tier(product_type: str, tier: int) -> bool:
    if tier == 1:
        return product_type in TIER_1_PRODUCT_TYPES
    if tier == 2:
        return product_type in TIER_2_PRODUCT_TYPES
    return False


def _build_action_recommendation(
    *,
    tier: int,
    institution_name: str,
    prep: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tier": tier,
        "recommendation_type": "relationship_action",
        "institution_name": institution_name,
        "product_name": f"{institution_name} relationship prep",
        "product_type": "banking_relationship_action" if tier == 1 else "relationship_based_lending",
        "approval_score": 0.0,
        "approval_score_without_relationship": 0.0,
        "relationship_boost": 0.0,
        "expected_limit_low": 0.0,
        "expected_limit_high": 0.0,
        "confidence_level": "educational",
        "reason": prep["summary"],
        "prep_steps": prep["recommended_prep_steps"],
        "evidence_summary": {"kind": "relationship_prep"},
        "disclaimer": DISCLAIMER,
        "status": "recommended",
    }


def generate_recommendations(
    *,
    user_profile: dict[str, Any],
    readiness_score: float,
    institutions: list[dict[str, Any]] | None = None,
    approval_patterns: list[dict[str, Any]] | None = None,
    tier: int | None = None,
) -> list[dict[str, Any]]:
    institutions = institutions or []
    approval_patterns = approval_patterns or []
    tiers = [tier] if tier else [1, 2]
    recommendations: list[dict[str, Any]] = []

    for row in institutions:
        product_types = row.get("product_types") or []
        institution_name = row.get("institution_name") or "Unknown institution"
        relationship_input = {
            "institution_name": institution_name,
            "account_open_date": user_profile.get("account_open_date"),
            "account_age_days": user_profile.get("account_age_days"),
            "average_balance": user_profile.get("average_balance"),
            "monthly_deposits": user_profile.get("monthly_deposits"),
            "deposit_consistency": user_profile.get("deposit_consistency"),
            "prior_products": user_profile.get("prior_products"),
            "verification_status": user_profile.get("verification_status"),
            "proof_url": user_profile.get("proof_url"),
        }
        relationship = score_relationship(relationship_input, row)
        matching_patterns = [
            pattern for pattern in approval_patterns
            if (pattern.get("bank_name") or "").lower() == institution_name.lower()
        ]

        for candidate_tier in tiers:
            for product_type in product_types:
                if not _matches_tier(product_type, candidate_tier):
                    continue
                label = (
                    "Credit union business credit card"
                    if product_type == "credit_union_business_credit_card"
                    else product_type.replace("_", " ").title()
                )
                scored = score_approval_recommendation(
                    product={
                        "tier": candidate_tier,
                        "min_score": row.get("min_score"),
                        "product_type": product_type,
                        "institution_name": institution_name,
                    },
                    user_profile=user_profile,
                    readiness_score=readiness_score,
                    relationship_score=relationship["relationship_score"],
                    approval_patterns=matching_patterns,
                )
                prep = recommend_relationship_prep(user_profile, row)
                recommendations.append({
                    "tier": candidate_tier,
                    "recommendation_type": "funding_product",
                    "institution_name": institution_name,
                    "product_name": f"{institution_name} {label}",
                    "product_type": product_type,
                    "approval_score": scored["approval_score"],
                    "approval_score_without_relationship": scored["approval_score_without_relationship"],
                    "relationship_boost": scored["relationship_boost"],
                    "expected_limit_low": scored["expected_limit_low"],
                    "expected_limit_high": scored["expected_limit_high"],
                    "confidence_level": scored["confidence_level"],
                    "reason": scored["reason"],
                    "prep_steps": prep["recommended_prep_steps"],
                    "evidence_summary": scored["evidence_summary"],
                    "disclaimer": DISCLAIMER,
                    "status": "recommended",
                })

            if candidate_tier == 1 and (
                row.get("business_checking_available") or row.get("membership_required")
            ):
                prep = recommend_relationship_prep(user_profile, row)
                recommendations.append(
                    _build_action_recommendation(
                        tier=1,
                        institution_name=institution_name,
                        prep=prep,
                    )
                )

    starter_name = "Starter business tradeline sequence"
    if 1 in tiers:
        recommendations.append({
            "tier": 1,
            "recommendation_type": "education_action",
            "institution_name": "Nexus",
            "product_name": starter_name,
            "product_type": "starter_tradeline",
            "approval_score": min(95.0, readiness_score),
            "approval_score_without_relationship": min(95.0, readiness_score),
            "relationship_boost": 0.0,
            "expected_limit_low": 0.0,
            "expected_limit_high": 0.0,
            "confidence_level": "educational",
            "reason": "Use starter tradelines and profile-building actions to improve fundability before broader applications.",
            "prep_steps": [
                "Add starter business tradelines that report cleanly to business bureaus.",
                "Verify business identity consistency before any funding applications.",
                "Document execution history inside Nexus after each completed step.",
            ],
            "evidence_summary": {"kind": "starter_tradeline_sequence"},
            "disclaimer": DISCLAIMER,
            "status": "recommended",
        })

    recommendations.sort(
        key=lambda row: (
            -float(row.get("approval_score") or 0),
            row.get("tier") or 99,
            row.get("institution_name") or "",
        )
    )
    return recommendations
