from __future__ import annotations

from lib.growth_support import safe_insert

ORDER = [
    "signup completed",
    "email verified",
    "profile started",
    "business setup started",
    "credit report uploaded",
    "funding roadmap viewed",
    "first action completed",
    "subscription activated",
]


def evaluate_onboarding(events: list[str]) -> dict:
    done = set(events)
    user_stage = next((stage for stage in ORDER if stage not in done), "subscription activated")
    completed_count = sum(1 for stage in ORDER if stage in done)
    if completed_count >= 6:
        risk = "low"
    elif completed_count >= 3:
        risk = "medium"
    else:
        risk = "high"
    message = {
        "email verified": "Confirm email and complete the first profile steps.",
        "profile started": "Finish the profile so your business readiness can be evaluated.",
        "business setup started": "Start the business setup checklist before applying anywhere.",
        "credit report uploaded": "Upload the credit report so readiness gaps can be identified.",
        "funding roadmap viewed": "View the roadmap before making funding moves.",
        "first action completed": "Take one concrete action so progress starts compounding.",
        "subscription activated": "You are close. Finish activation only after you understand the path.",
    }.get(user_stage, "Keep the next step simple and obvious.")
    agent = "onboarding_agent" if risk != "low" else "marketing_strategist"
    return {
        "user_stage": user_stage,
        "dropoff_risk": risk,
        "recommended_message": message,
        "recommended_admin_action": "Review friction points and simplify the next step.",
        "recommended_agent": agent,
    }


def save_onboarding_recommendation(user_ref: str, events: list[str]) -> dict:
    result = evaluate_onboarding(events)
    safe_insert("onboarding_dropoffs", {
        "user_ref": user_ref,
        "stage": result["user_stage"],
        "risk_level": result["dropoff_risk"],
        "notes": result["recommended_message"],
    })
    return safe_insert("onboarding_recommendations", {
        "user_ref": user_ref,
        "user_stage": result["user_stage"],
        "recommended_message": result["recommended_message"],
        "recommended_admin_action": result["recommended_admin_action"],
        "recommended_agent": result["recommended_agent"],
    })
