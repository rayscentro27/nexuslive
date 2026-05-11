from __future__ import annotations

from statistics import median
from typing import Any

from funding_engine.constants import DISCLAIMER


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _bucket_match_score(user_value: float, min_value: float) -> float:
    if user_value <= 0 or min_value <= 0:
        return 0.0
    if user_value >= min_value + 40:
        return 1.0
    if user_value >= min_value + 20:
        return 0.85
    if user_value >= min_value:
        return 0.7
    if user_value >= min_value - 20:
        return 0.45
    return 0.2


def _confidence_level(sample_size: float, confidence_score: float) -> str:
    combined = sample_size * 0.6 + confidence_score * 40
    if combined >= 80:
        return "high"
    if combined >= 45:
        return "medium"
    return "low"


def _expected_limits(pattern_rows: list[dict[str, Any]], approval_score: float, tier: int) -> tuple[float, float]:
    limits = [_as_float(row.get("avg_limit")) for row in pattern_rows if _as_float(row.get("avg_limit")) > 0]
    maxima = [_as_float(row.get("max_limit")) for row in pattern_rows if _as_float(row.get("max_limit")) > 0]
    base_mid = median(limits) if limits else (5000.0 if tier == 1 else 25000.0)
    max_hint = max(maxima) if maxima else (15000.0 if tier == 1 else 150000.0)
    multiplier = max(0.45, min(approval_score / 100.0, 1.1))
    low = round(base_mid * 0.5 * multiplier, 2)
    high = round(min(max_hint, base_mid * 1.5 * multiplier + (2000 if tier == 1 else 10000)), 2)
    if high < low:
        high = low
    return low, high


def score_approval_recommendation(
    *,
    product: dict[str, Any],
    user_profile: dict[str, Any],
    readiness_score: float,
    relationship_score: float = 0.0,
    approval_patterns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    approval_patterns = approval_patterns or []
    tier = int(product.get("tier") or 1)
    min_score = _as_float(product.get("min_score"))
    user_credit_score = _as_float(user_profile.get("personal_credit_score"))
    monthly_deposits = _as_float(user_profile.get("monthly_deposits"))
    annual_income = _as_float(user_profile.get("annual_income"))

    credit_component = _bucket_match_score(user_credit_score, min_score) * 35
    readiness_component = max(0.0, min(readiness_score, 100.0)) * 0.35
    deposit_component = 0.0
    if monthly_deposits >= 10000:
        deposit_component = 10
    elif monthly_deposits >= 5000:
        deposit_component = 7
    elif monthly_deposits > 0:
        deposit_component = 4

    pattern_component = 0.0
    pattern_confidence = 0.0
    if approval_patterns:
        weighted_rates = []
        for row in approval_patterns:
            rate = _as_float(row.get("approval_rate"))
            sample = _as_float(row.get("sample_size"))
            confidence = _as_float(row.get("confidence_score"))
            if rate > 0:
                weighted_rates.append(rate * max(sample, 1))
            pattern_confidence = max(pattern_confidence, confidence)
        if weighted_rates:
            pattern_component = min(sum(weighted_rates) / max(len(weighted_rates), 1), 15.0)

    base_score = credit_component + readiness_component + deposit_component + pattern_component
    without_relationship = round(max(5.0, min(base_score, 95.0)), 2)
    relationship_boost = round(min(12.0, max(0.0, relationship_score) * 0.6), 2)
    approval_score = round(min(99.0, without_relationship + relationship_boost), 2)
    expected_low, expected_high = _expected_limits(approval_patterns, approval_score, tier)

    reason_bits = [
        f"Internal readiness score: {round(readiness_score, 1)}/100",
        f"Personal credit support: {round(user_credit_score, 0) if user_credit_score else 'unknown'}",
        f"Relationship strength: {round(relationship_score, 1)}/20",
    ]
    if annual_income:
        reason_bits.append(f"Income signal present: {round(annual_income, 0):,.0f}")
    reason = "; ".join(reason_bits) + ". Results vary. Approval is determined by the lender and is not guaranteed."

    sample_size = max((_as_float(row.get("sample_size")) for row in approval_patterns), default=0.0)
    confidence_level = _confidence_level(sample_size, pattern_confidence)
    evidence_summary = {
        "tier": tier,
        "pattern_count": len(approval_patterns),
        "top_pattern_sources": [
            {
                "bank_name": row.get("bank_name"),
                "card_name": row.get("card_name"),
                "approval_rate": row.get("approval_rate"),
                "sample_size": row.get("sample_size"),
            }
            for row in approval_patterns[:3]
        ],
        "relationship_considered": relationship_score > 0,
    }
    return {
        "approval_score": approval_score,
        "approval_score_without_relationship": without_relationship,
        "relationship_boost": relationship_boost,
        "expected_limit_low": expected_low,
        "expected_limit_high": expected_high,
        "confidence_level": confidence_level,
        "reason": reason,
        "evidence_summary": evidence_summary,
        "disclaimer": DISCLAIMER,
    }
