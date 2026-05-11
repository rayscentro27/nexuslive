#!/usr/bin/env python3
"""Lightweight acceptance checks for Hermes Chief-of-Staff flows."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check(label: str, cond: bool, detail: str = "") -> bool:
    ok = "PASS" if cond else "FAIL"
    print(f"[{ok}] {label}" + (f" — {detail}" if detail else ""))
    return cond


def main() -> int:
    ok = True

    from ceo_agent.chief_of_staff import (
        build_business_digest,
        build_daily_executive_summary,
        build_grants_digest,
        build_trading_digest,
        build_website_brief,
    )
    from ceo_agent.recommendation_queue import format_recommendations, seed_default_recommendations
    from ceo_agent.telemetry_rollups import generate_daily_rollups
    from telegram_bot import NexusTelegramBot

    trading = build_trading_digest()
    business = build_business_digest()
    grants = build_grants_digest()
    daily = build_daily_executive_summary()
    brief = build_website_brief(business.get("top") or {"title": "Sample", "niche": "services", "description": "Offer"})

    ok &= _check("trading digest returns text", isinstance(trading.get("text"), str) and len(trading.get("text")) > 0)
    ok &= _check("business digest returns text", isinstance(business.get("text"), str) and len(business.get("text")) > 0)
    ok &= _check("grants digest returns text", isinstance(grants.get("text"), str) and len(grants.get("text")) > 0)
    ok &= _check("daily summary returns text", isinstance(daily, str) and len(daily) > 0)
    ok &= _check("website brief includes required sections", "Website Build Brief" in brief and "First 7-day launch plan" in brief)
    seed_default_recommendations()
    recs = format_recommendations(pending_only=True)
    ok &= _check("recommendation queue formats", isinstance(recs, str) and len(recs) > 0)
    rollups = generate_daily_rollups()
    ok &= _check("daily telemetry rollups return summary", isinstance(rollups, dict) and "trading" in rollups and "business" in rollups)

    bot = NexusTelegramBot()
    checks = {
        "summarize today": "daily_summary",
        "show trading digest": "trading_digest",
        "what strategies should we improve?": "strategy_improve",
        "what business should we build next?": "business_next",
        "show best online opportunities": "online_opportunities",
        "generate website brief for the top opportunity": "website_brief",
        "show critical alerts": "critical_alerts",
        "what needs my approval?": "approvals",
        "show recommendations": "show_recommendations",
        "show pending recommendations": "show_pending_recommendations",
        "what should we focus on this week?": "weekly_focus",
        "highest roi opportunity": "highest_roi",
        "best business to launch": "best_business_launch",
        "best performing strategy": "best_strategy",
        "what should we stop doing?": "stop_doing",
        "what should we automate next?": "automate_next",
        "show recommendation rankings": "recommendation_rankings",
        "what credit actions work best?": "credit_actions_best",
        "what is blocking funding approvals?": "funding_blockers",
        "which lenders approve most often?": "lender_approvals",
        "what profile patterns succeed?": "profile_patterns",
        "what should improve before applying?": "pre_apply_improvements",
        "which clients are closest to tier 1 readiness?": "tier1_closest",
        "what credit strategies improve scores fastest?": "credit_strategies_fastest",
        "which clients are closest to funding?": "clients_closest_funding",
        "which clients are stuck?": "clients_stuck",
        "who is likely to churn?": "clients_churn",
        "who needs intervention?": "clients_intervention",
        "highest momentum clients": "clients_momentum",
        "highest value clients": "clients_value",
        "who should we prioritize this week?": "clients_weekly_priority",
        "which clients need outreach?": "clients_outreach",
        "why did hermes recommend this?": "why_recommended",
        "show recommendation reasoning": "recommendation_reasoning",
        "what signals influenced this score?": "score_signals",
        "what data is missing?": "missing_data",
        "why is this client high priority?": "client_priority_reason",
        "why is this strategy ranked highly?": "strategy_priority_reason",
        "show executive review snapshot": "executive_review_snapshot",
    }
    for phrase, expected in checks.items():
        got, _ = bot.parse_command(phrase)
        ok &= _check(f"parse command: {phrase}", got == expected, f"got={got} expected={expected}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
