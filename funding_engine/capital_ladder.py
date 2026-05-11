from __future__ import annotations

from typing import Any

from funding_engine.constants import DISCLAIMER


CAPITAL_LADDER = {
    1: {
        "name": "Tier 1",
        "description": "Starter funding and profile building.",
        "products": [
            "bank business credit cards",
            "credit union business credit cards",
            "starter business tradelines",
            "starter banking relationship actions",
        ],
    },
    2: {
        "name": "Tier 2",
        "description": "Credit union LOC, SBA, and larger lending.",
        "products": [
            "credit union LOCs",
            "SBA microloans",
            "working capital loans",
            "larger credit union lending products",
            "relationship-based lending products",
        ],
    },
    3: {
        "name": "Tier 3",
        "description": "Advanced capital strategy.",
        "products": [
            "advanced capital stack planning",
            "relationship-led expansion financing",
            "portfolio capital sequencing",
        ],
    },
}


def get_capital_ladder() -> dict[int, dict[str, Any]]:
    return CAPITAL_LADDER


def evaluate_tier_progress(
    *,
    readiness_score: float,
    relationship_score: float,
    tier_1_actions_completed: int = 0,
    reported_tier_1_results_count: int = 0,
    relationship_prep_completed: bool = False,
    relationship_prep_scheduled: bool = False,
) -> dict[str, Any]:
    tier_1_status = "in_progress"
    if tier_1_actions_completed >= 3 and readiness_score >= 55:
        tier_1_status = "ready"
    if reported_tier_1_results_count >= 1:
        tier_1_status = "completed"

    tier_2_ready = (
        tier_1_actions_completed >= 3
        and readiness_score >= 70
        and (relationship_prep_completed or relationship_prep_scheduled or relationship_score >= 10)
    )
    tier_2_status = "unlocked" if tier_2_ready else "locked"

    tier_3_status = "locked"
    if reported_tier_1_results_count >= 2 and readiness_score >= 82 and relationship_score >= 14:
        tier_3_status = "ready_for_strategy_review"

    current_tier = 1
    if tier_2_ready:
        current_tier = 2
    if tier_3_status == "ready_for_strategy_review":
        current_tier = 3

    missing: list[str] = []
    if tier_1_actions_completed < 3:
        missing.append("Complete or report Tier 1 preparation actions.")
    if readiness_score < 70:
        missing.append("Increase the internal Nexus readiness score before Tier 2.")
    if not (relationship_prep_completed or relationship_prep_scheduled or relationship_score >= 10):
        missing.append("Complete or schedule banking relationship prep.")

    return {
        "current_tier": current_tier,
        "tier_1_status": tier_1_status,
        "tier_2_status": tier_2_status,
        "tier_3_status": tier_3_status,
        "tier_2_unlock_ready": tier_2_ready,
        "missing_for_tier_2": missing,
        "disclaimer": DISCLAIMER,
    }
