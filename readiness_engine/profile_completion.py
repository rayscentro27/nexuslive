"""
profile_completion.py — Calculate completion percentages for each client readiness section.

Each section returns a dict with:
  - completed: int (fields that have a value)
  - total: int (fields in section)
  - pct: float (0.0–1.0)
  - missing_fields: list[str]
"""
from __future__ import annotations

from typing import Any


def _has_value(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return True
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def _section(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    missing = [f for f in fields if not _has_value(data.get(f))]
    completed = len(fields) - len(missing)
    return {
        "completed": completed,
        "total": len(fields),
        "pct": round(completed / len(fields), 4) if fields else 0.0,
        "missing_fields": missing,
    }


BUSINESS_FOUNDATION_FIELDS = [
    "legal_business_name",
    "entity_type",
    "state_formed",
    "ein_status",
    "business_address_status",
    "business_phone_status",
    "business_email_domain_status",
    "website_status",
    "naics_code",
    "industry",
    "time_in_business_months",
    "monthly_revenue",
    "employee_count",
    "business_bank_account_status",
]

CREDIT_PROFILE_FIELDS = [
    "personal_credit_score_estimate",
    "credit_utilization",
    "inquiries_count",
    "negative_items_count",
    "age_of_credit_history",
    "credit_report_uploaded",
    "duns_status",
]

BANKING_SETUP_FIELDS = [
    "current_business_bank",
    "account_age_months",
    "average_balance",
    "monthly_deposits",
    "nsf_count",
    "verification_status",
]

GRANT_ELIGIBILITY_FIELDS = [
    "business_location_state",
    "business_location_city",
    "industry",
    "revenue_range",
    "employee_count",
    "business_stage",
    "use_of_funds",
]

TRADING_ELIGIBILITY_FIELDS = [
    "capital_reserve",
    "risk_tolerance",
    "education_video_completed",
    "disclaimer_accepted",
    "paper_trading_completed",
]


def business_foundation_completion(data: dict[str, Any]) -> dict[str, Any]:
    return _section(data, BUSINESS_FOUNDATION_FIELDS)


def credit_profile_completion(data: dict[str, Any]) -> dict[str, Any]:
    return _section(data, CREDIT_PROFILE_FIELDS)


def banking_setup_completion(data: dict[str, Any]) -> dict[str, Any]:
    return _section(data, BANKING_SETUP_FIELDS)


def grant_eligibility_completion(data: dict[str, Any]) -> dict[str, Any]:
    return _section(data, GRANT_ELIGIBILITY_FIELDS)


def trading_eligibility_completion(data: dict[str, Any]) -> dict[str, Any]:
    return _section(data, TRADING_ELIGIBILITY_FIELDS)


def overall_profile_completion(
    foundation: dict[str, Any],
    credit: dict[str, Any],
    banking: dict[str, Any],
    grants: dict[str, Any],
    trading: dict[str, Any],
) -> dict[str, Any]:
    sections = {
        "business_foundation": foundation,
        "credit_profile": credit,
        "banking_setup": banking,
        "grant_eligibility": grants,
        "trading_eligibility": trading,
    }
    total_fields = sum(s["total"] for s in sections.values())
    total_completed = sum(s["completed"] for s in sections.values())
    overall_pct = round(total_completed / total_fields, 4) if total_fields else 0.0
    return {
        "overall_pct": overall_pct,
        "total_completed": total_completed,
        "total_fields": total_fields,
        "sections": {k: {"pct": v["pct"], "missing_fields": v["missing_fields"]} for k, v in sections.items()},
    }
