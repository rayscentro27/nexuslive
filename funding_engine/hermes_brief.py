from __future__ import annotations

from typing import Any

from funding_engine.constants import DISCLAIMER


def build_daily_capital_brief(snapshot: dict[str, Any]) -> dict[str, Any]:
    top_move = snapshot.get("top_tier_1_move") or "Review Tier 1 readiness and complete the next practical action."
    relationship_move = snapshot.get("relationship_move") or "Strengthen the target banking relationship with consistent deposits and documented proof."
    opportunity = snapshot.get("credit_union_opportunity") or "Review one credit union business card or LOC opportunity that matches your profile."
    readiness_score = snapshot.get("readiness_score", "unknown")
    missing_data = snapshot.get("missing_data") or ["Business score inputs", "Banking relationship inputs"]
    tier_progress = snapshot.get("tier_progress") or "Tier progress not yet calculated."
    referral_reminder = snapshot.get("referral_earnings_reminder") or "Referral earnings appear after a referred user receives eligible Tier 1 or Tier 2 funding."

    lines = [
        "Today's Funding Move:",
        f"{top_move}",
        "",
        "Relationship-Building Move:",
        f"{relationship_move}",
        "",
        "Credit Union / Business Card Opportunity:",
        f"{opportunity}",
        "",
        "Readiness Score Update:",
        f"{readiness_score}",
        "",
        "Missing Data Needed:",
        *[f"- {item}" for item in missing_data],
        "",
        "Tier Unlock Progress:",
        f"{tier_progress}",
        "",
        "Referral Earnings Reminder:",
        f"{referral_reminder}",
        "",
        DISCLAIMER,
    ]
    return {
        "brief_text": "\n".join(lines),
        "disclaimer": DISCLAIMER,
    }
