from __future__ import annotations

from lib.growth_support import default_test_mode, safe_insert


def score_lead(payload: dict) -> dict:
    credit = int(payload.get("credit_readiness", 0))
    business = int(payload.get("business_readiness", 0))
    funding = int(payload.get("funding_intent", 0))
    engagement = int(payload.get("engagement_level", 0))
    subscription = int(payload.get("subscription_likelihood", 0))
    commission = int(payload.get("commission_opportunity", 0))
    compliance = int(payload.get("compliance_sensitivity", 0))
    lead_score = max(0, min(100, round((credit + business + funding + engagement + subscription + commission + (100 - compliance)) / 7)))
    if credit < 40:
        segment = "needs_credit_repair"
        next_step = "Improve personal/business credit profile and consistency."
        agent = "credit_analyst"
    elif business < 45:
        segment = "business_setup_needed"
        next_step = "Tighten entity setup, contact consistency, and credibility signals."
        agent = "business_formation"
    elif funding >= 70 and credit >= 60 and business >= 60:
        segment = "funding_ready"
        next_step = "Review funding timing and Tier 1 options."
        agent = "funding_strategist"
    elif lead_score >= 70:
        segment = "hot"
        next_step = "Offer the clearest next readiness action."
        agent = "marketing_strategist"
    elif lead_score >= 45:
        segment = "warm"
        next_step = "Nurture with education-first content and setup help."
        agent = "content_creator"
    else:
        segment = "cold"
        next_step = "Start with foundational educational content."
        agent = "content_creator"
    return {
        "lead_score": lead_score,
        "segment": segment,
        "recommended_next_step": next_step,
        "recommended_agent": agent,
        "risk_notes": "No guarantees. Use education-first and review sensitive claims.",
        "score_payload": payload,
    }


def save_lead_score(lead_ref: str, payload: dict) -> dict:
    result = score_lead(payload)
    return safe_insert("lead_scores", {
        "lead_ref": lead_ref,
        "lead_score": result["lead_score"],
        "segment": result["segment"],
        "recommended_next_step": result["recommended_next_step"],
        "recommended_agent": result["recommended_agent"],
        "risk_notes": result["risk_notes"],
        "score_payload": {"input": payload, "test_mode_default": default_test_mode()},
    }, prefer="resolution=merge-duplicates,return=representation")
