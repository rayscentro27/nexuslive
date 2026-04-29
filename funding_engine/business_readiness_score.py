from __future__ import annotations

from typing import Any


MAX_SECTION_SCORES = {
    "business_foundation": 20,
    "business_credit_profile": 20,
    "personal_credit_support": 15,
    "cash_flow_bankability": 15,
    "banking_relationships": 20,
    "execution_history": 10,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def calculate_business_readiness_score(
    profile: dict[str, Any] | None = None,
    business_score_inputs: dict[str, Any] | None = None,
    relationships: list[dict[str, Any]] | None = None,
    execution_history: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Calculate the internal Nexus Business Funding Readiness Score (0-100).
    This is not a bureau score and should not be represented as one.
    """
    profile = profile or {}
    business_score_inputs = business_score_inputs or {}
    relationships = relationships or []
    execution_history = execution_history or {}

    foundation = 0.0
    foundation += 5 if profile.get("business_registered") else 0
    foundation += 4 if profile.get("ein_present") else 0
    foundation += 3 if profile.get("business_address_present") else 0
    foundation += 3 if profile.get("professional_email_present") else 0
    foundation += 3 if profile.get("website_present") else 0
    foundation += 2 if profile.get("phone_listed") else 0
    foundation = _clamp(foundation, 0, MAX_SECTION_SCORES["business_foundation"])

    tradelines = _as_float(business_score_inputs.get("reporting_tradelines_count"))
    paydex = _as_float(business_score_inputs.get("paydex_score"))
    experian = _as_float(business_score_inputs.get("experian_business_score"))
    equifax = _as_float(business_score_inputs.get("equifax_business_score"))
    credit_profile = 0.0
    if str(business_score_inputs.get("duns_status", "")).lower() in {"active", "established", "verified"}:
        credit_profile += 5
    if tradelines >= 3:
        credit_profile += 6
    elif tradelines >= 1:
        credit_profile += 3
    if paydex >= 75:
        credit_profile += 4
    elif paydex >= 60:
        credit_profile += 2
    if experian >= 70 or equifax >= 70:
        credit_profile += 3
    if str(business_score_inputs.get("nav_grade", "")).strip():
        credit_profile += 2
    credit_profile = _clamp(credit_profile, 0, MAX_SECTION_SCORES["business_credit_profile"])

    personal_score = _as_float(profile.get("personal_credit_score"))
    personal_support = 0.0
    if personal_score >= 720:
        personal_support += 10
    elif personal_score >= 680:
        personal_support += 8
    elif personal_score >= 640:
        personal_support += 5
    elif personal_score >= 600:
        personal_support += 3
    personal_support += 3 if not profile.get("high_utilization") else 0
    personal_support += 2 if not profile.get("recent_late_payments") else 0
    personal_support += 2 if profile.get("low_inquiry_velocity") else 0
    personal_support = _clamp(personal_support, 0, MAX_SECTION_SCORES["personal_credit_support"])

    deposits = _as_float(business_score_inputs.get("monthly_deposits"))
    avg_balance = _as_float(business_score_inputs.get("average_balance"))
    bank_age_months = _as_float(business_score_inputs.get("business_bank_account_age_months"))
    nsf_count = _as_float(business_score_inputs.get("nsf_count"))
    cash_flow = 0.0
    if bank_age_months >= 6:
        cash_flow += 4
    elif bank_age_months >= 3:
        cash_flow += 2
    if deposits >= 10000:
        cash_flow += 4
    elif deposits >= 5000:
        cash_flow += 3
    elif deposits > 0:
        cash_flow += 1
    if avg_balance >= 5000:
        cash_flow += 4
    elif avg_balance >= 2500:
        cash_flow += 2
    if str(business_score_inputs.get("revenue_consistency", "")).lower() in {"consistent", "stable"}:
        cash_flow += 3
    if nsf_count <= 0:
        cash_flow += 2
    elif nsf_count <= 1:
        cash_flow += 1
    cash_flow = _clamp(cash_flow, 0, MAX_SECTION_SCORES["cash_flow_bankability"])

    relationship_scores = [_as_float(row.get("relationship_score")) for row in relationships]
    best_relationship = max(relationship_scores) if relationship_scores else 0.0
    relationship_section = _clamp(best_relationship, 0, MAX_SECTION_SCORES["banking_relationships"])

    reported_results = _as_float(execution_history.get("reported_results_count"))
    verified_results = _as_float(execution_history.get("verified_results_count"))
    completed_actions = _as_float(execution_history.get("completed_actions_count"))
    execution = 0.0
    if completed_actions >= 3:
        execution += 4
    elif completed_actions >= 1:
        execution += 2
    if reported_results >= 1:
        execution += 3
    if verified_results >= 1:
        execution += 3
    execution = _clamp(execution, 0, MAX_SECTION_SCORES["execution_history"])

    breakdown = {
        "business_foundation": round(foundation, 2),
        "business_credit_profile": round(credit_profile, 2),
        "personal_credit_support": round(personal_support, 2),
        "cash_flow_bankability": round(cash_flow, 2),
        "banking_relationships": round(relationship_section, 2),
        "execution_history": round(execution, 2),
    }
    total = round(sum(breakdown.values()), 2)
    return {
        "score": _clamp(total, 0, 100),
        "breakdown": breakdown,
        "label": (
            "strong" if total >= 80 else
            "progressing" if total >= 60 else
            "early"
        ),
        "is_internal_nexus_score": True,
        "note": "Internal Nexus readiness score only. Not a bureau score.",
    }
