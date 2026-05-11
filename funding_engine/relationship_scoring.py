from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _today() -> date:
    return datetime.utcnow().date()


def _days_open(account_open_date: str | date | None, fallback_days: int | None = None) -> int:
    if fallback_days is not None:
        return max(int(fallback_days), 0)
    if not account_open_date:
        return 0
    if isinstance(account_open_date, date):
        opened = account_open_date
    else:
        opened = date.fromisoformat(str(account_open_date))
    return max((_today() - opened).days, 0)


def score_relationship(user_relationship: dict[str, Any], institution: dict[str, Any] | None = None) -> dict[str, Any]:
    institution = institution or {}
    rel = user_relationship or {}
    score = 0
    reasons: list[str] = []
    institution_name = institution.get("institution_name") or rel.get("institution_name")

    if rel.get("institution_name"):
        score += 4
        reasons.append("Existing account relationship")

    age_days = _days_open(rel.get("account_open_date"), rel.get("account_age_days"))
    if age_days >= 90:
        score += 5
        reasons.append("Account aged 90+ days")
    elif age_days >= 30:
        score += 3
        reasons.append("Account aged 30+ days")

    avg_balance = float(rel.get("average_balance") or 0)
    if avg_balance > 10000:
        score += 7
        reasons.append("Average balance above $10K")
    elif avg_balance > 5000:
        score += 5
        reasons.append("Average balance above $5K")
    elif avg_balance > 2500:
        score += 3
        reasons.append("Average balance above $2.5K")

    consistency = str(rel.get("deposit_consistency") or "").lower()
    monthly_deposits = float(rel.get("monthly_deposits") or 0)
    if consistency in {"consistent", "stable", "regular"} or monthly_deposits >= 2500:
        score += 3
        reasons.append("Consistent monthly deposits")

    prior_products = rel.get("prior_products") or []
    if prior_products:
        score += 2
        reasons.append("Prior product with institution")

    verification_status = str(rel.get("verification_status") or "").lower()
    if rel.get("proof_url") or verification_status in {"verified", "documented"}:
        score += 2
        reasons.append("Proof uploaded or verified")

    score = min(score, 20)
    return {
        "institution_name": institution_name,
        "relationship_score": score,
        "reasons": reasons,
        "cap": 20,
        "note": "Relationship strength may help with readiness, but does not guarantee approval.",
    }


def recommend_relationship_prep(
    user_profile: dict[str, Any] | None,
    target_institution: dict[str, Any] | None,
) -> dict[str, Any]:
    user_profile = user_profile or {}
    target_institution = target_institution or {}
    institution_name = target_institution.get("institution_name") or "the target institution"
    avg_balance = float(user_profile.get("average_balance") or 0)
    business_checking = bool(target_institution.get("business_checking_available"))
    membership_required = bool(target_institution.get("membership_required"))

    steps: list[str] = []
    if business_checking:
        steps.append(f"Open business checking with {institution_name} if you do not already have it.")
    if membership_required:
        steps.append(f"Confirm membership eligibility requirements for {institution_name} before applying.")
    if avg_balance < 5000:
        steps.append("Build toward a $5K+ average balance if practical before the application window.")
    steps.append("Maintain 30-90 days of clean business deposits and keep account activity consistent.")
    steps.append("Upload supporting proof or statements so the relationship can be documented inside Nexus.")

    summary = (
        f"Open business checking with {institution_name}, maintain $5K+ average balance for 30-90 days, "
        "and keep deposits consistent before applying."
    )
    return {
        "institution_name": institution_name,
        "recommended_prep_steps": steps,
        "summary": summary,
        "note": "This may improve relationship strength, but approval is not guaranteed.",
    }
