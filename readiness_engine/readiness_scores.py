"""
readiness_scores.py — Section and composite readiness scores for client profiles.

Scores are internal Nexus metrics only. They are not bureau scores,
credit ratings, or approval guarantees.
"""
from __future__ import annotations

from typing import Any

SCORE_NOTE = (
    "This is an internal Nexus readiness estimate only. "
    "It does not represent a credit score, bureau rating, or approval guarantee."
)

_SECTION_WEIGHTS = {
    "business_foundation": 0.25,
    "credit_profile": 0.25,
    "banking_setup": 0.20,
    "grant_eligibility": 0.15,
    "trading_eligibility": 0.15,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def _as_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def score_business_foundation(data: dict[str, Any]) -> dict[str, Any]:
    points = 0.0

    if data.get("legal_business_name"):
        points += 8
    if data.get("entity_type"):
        points += 5
    if data.get("state_formed"):
        points += 3
    if str(data.get("ein_status", "")).lower() in {"active", "issued"}:
        points += 12
    if str(data.get("business_address_status", "")).lower() in {"active", "verified"}:
        points += 8
    if str(data.get("business_phone_status", "")).lower() in {"active", "listed"}:
        points += 5
    if str(data.get("business_email_domain_status", "")).lower() in {"active", "verified"}:
        points += 7
    if str(data.get("website_status", "")).lower() in {"active", "live"}:
        points += 7
    if data.get("naics_code"):
        points += 5
    if data.get("industry"):
        points += 3

    tib = _as_int(data.get("time_in_business_months"))
    if tib >= 24:
        points += 15
    elif tib >= 12:
        points += 10
    elif tib >= 6:
        points += 5

    rev = _as_float(data.get("monthly_revenue"))
    if rev >= 10000:
        points += 10
    elif rev >= 4000:
        points += 6
    elif rev > 0:
        points += 2

    if str(data.get("business_bank_account_status", "")).lower() in {"active", "open", "verified"}:
        points += 12

    score = _clamp(points, 0, 100)
    return {"score": round(score, 1), "note": SCORE_NOTE}


def score_credit_profile(data: dict[str, Any]) -> dict[str, Any]:
    points = 0.0

    score_est = _as_int(data.get("personal_credit_score_estimate"))
    if score_est >= 720:
        points += 30
    elif score_est >= 680:
        points += 22
    elif score_est >= 640:
        points += 14
    elif score_est > 0:
        points += 6

    exp = _as_int(data.get("experian_score"))
    eq = _as_int(data.get("equifax_score"))
    tu = _as_int(data.get("transunion_score"))
    bureau_scores = [s for s in [exp, eq, tu] if s > 0]
    if bureau_scores:
        avg_bureau = sum(bureau_scores) / len(bureau_scores)
        if avg_bureau >= 720:
            points += 10
        elif avg_bureau >= 680:
            points += 7
        elif avg_bureau >= 640:
            points += 4

    util = _as_float(data.get("credit_utilization"))
    if 0 <= util <= 0.15:
        points += 15
    elif util <= 0.30:
        points += 10
    elif util <= 0.50:
        points += 4

    inq = _as_int(data.get("inquiries_count"))
    if inq == 0:
        points += 8
    elif inq <= 2:
        points += 5
    elif inq <= 4:
        points += 2

    neg = _as_int(data.get("negative_items_count"))
    if neg == 0:
        points += 10
    elif neg == 1:
        points += 4

    age_months = _as_float(data.get("age_of_credit_history"))
    if age_months >= 84:
        points += 10
    elif age_months >= 48:
        points += 7
    elif age_months >= 24:
        points += 3

    if data.get("credit_report_uploaded"):
        points += 5

    if str(data.get("duns_status", "")).lower() in {"active", "issued"}:
        points += 7

    paydex = _as_int(data.get("paydex_score"))
    if paydex >= 80:
        points += 5

    score = _clamp(points, 0, 100)
    return {"score": round(score, 1), "note": SCORE_NOTE}


def score_banking_setup(data: dict[str, Any]) -> dict[str, Any]:
    points = 0.0

    if data.get("current_business_bank"):
        points += 15

    age = _as_int(data.get("account_age_months"))
    if age >= 12:
        points += 20
    elif age >= 6:
        points += 12
    elif age >= 3:
        points += 6
    elif age > 0:
        points += 2

    balance = _as_float(data.get("average_balance"))
    if balance >= 10000:
        points += 20
    elif balance >= 5000:
        points += 14
    elif balance >= 1000:
        points += 7
    elif balance > 0:
        points += 2

    deposits = _as_float(data.get("monthly_deposits"))
    if deposits >= 10000:
        points += 20
    elif deposits >= 5000:
        points += 13
    elif deposits >= 1000:
        points += 6
    elif deposits > 0:
        points += 2

    nsf = _as_int(data.get("nsf_count"))
    if nsf == 0:
        points += 15
    elif nsf <= 2:
        points += 5

    if str(data.get("verification_status", "")).lower() == "verified":
        points += 10

    score = _clamp(points, 0, 100)
    return {"score": round(score, 1), "note": SCORE_NOTE}


def score_grant_eligibility(data: dict[str, Any]) -> dict[str, Any]:
    points = 0.0

    if data.get("business_location_state"):
        points += 15
    if data.get("business_location_city"):
        points += 10
    if data.get("industry"):
        points += 10
    if data.get("revenue_range"):
        points += 10
    if data.get("business_stage"):
        points += 10
    if data.get("use_of_funds"):
        points += 15

    certs = data.get("certifications") or []
    if isinstance(certs, list) and len(certs) > 0:
        points += 10

    if data.get("grant_documents_uploaded"):
        points += 20

    score = _clamp(points, 0, 100)
    return {"score": round(score, 1), "note": SCORE_NOTE}


def score_trading_eligibility(data: dict[str, Any]) -> dict[str, Any]:
    points = 0.0

    reserve = _as_float(data.get("capital_reserve"))
    if reserve >= 5000:
        points += 20
    elif reserve >= 1000:
        points += 10
    elif reserve > 0:
        points += 4

    if data.get("risk_tolerance"):
        points += 10

    if data.get("education_video_completed"):
        points += 25
    if data.get("disclaimer_accepted"):
        points += 25
    if data.get("paper_trading_completed"):
        points += 20

    score = _clamp(points, 0, 100)
    return {"score": round(score, 1), "note": SCORE_NOTE}


def is_trading_eligible(trading_data: dict[str, Any]) -> bool:
    return bool(
        trading_data.get("education_video_completed")
        and trading_data.get("disclaimer_accepted")
        and trading_data.get("paper_trading_completed")
    )


def is_grant_ready(grant_data: dict[str, Any]) -> bool:
    required = ["business_location_state", "industry", "revenue_range", "business_stage", "use_of_funds"]
    return all(grant_data.get(f) for f in required)


def calculate_overall_readiness_score(
    foundation_score: float,
    credit_score: float,
    banking_score: float,
    grant_score: float,
    trading_score: float,
) -> dict[str, Any]:
    weighted = (
        foundation_score * _SECTION_WEIGHTS["business_foundation"]
        + credit_score * _SECTION_WEIGHTS["credit_profile"]
        + banking_score * _SECTION_WEIGHTS["banking_setup"]
        + grant_score * _SECTION_WEIGHTS["grant_eligibility"]
        + trading_score * _SECTION_WEIGHTS["trading_eligibility"]
    )
    score = _clamp(round(weighted, 1))
    return {
        "score": score,
        "breakdown": {
            "business_foundation": round(foundation_score, 1),
            "credit_profile": round(credit_score, 1),
            "banking_setup": round(banking_score, 1),
            "grant_eligibility": round(grant_score, 1),
            "trading_eligibility": round(trading_score, 1),
        },
        "weights": _SECTION_WEIGHTS,
        "note": SCORE_NOTE,
    }
