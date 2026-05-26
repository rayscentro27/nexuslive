"""
Nexus Scout Registry
=====================
Defines all intelligence scouts across two core divisions:
  - Division 1: Market Intelligence
  - Division 2: Monetization Intelligence

Each scout has a focused responsibility, schedule, KPIs, and evidence requirements.
Scouts run on recurring schedules, save findings to Supabase, and feed the Consensus Engine.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

DIVISION_MARKET_INTELLIGENCE = "market_intelligence"
DIVISION_MONETIZATION_INTELLIGENCE = "monetization_intelligence"

# ── Scout definitions ─────────────────────────────────────────────────────────

SCOUTS: list[dict] = [

    # ── Market Intelligence Division ─────────────────────────────────────────

    {
        "scout_id": "insider_scout",
        "division": DIVISION_MARKET_INTELLIGENCE,
        "name": "Insider Scout",
        "purpose": "Track insider buying/selling signals and executive transactions",
        "schedule_hours": 12,
        "success_metrics": ["insider_signal_count", "high_confidence_signals"],
        "failure_metrics": ["zero_signals_3_days", "stale_data"],
        "optimization_targets": ["signal_accuracy", "lead_time"],
        "output_types": ["market_briefing", "insider_signal_report"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "macro_scout",
        "division": DIVISION_MARKET_INTELLIGENCE,
        "name": "Macro Scout",
        "purpose": "Monitor macro economic indicators, Fed policy, sector rotation signals",
        "schedule_hours": 6,
        "success_metrics": ["macro_signals", "regime_accuracy"],
        "failure_metrics": ["missed_regime_shift", "stale_indicators"],
        "optimization_targets": ["regime_detection_accuracy"],
        "output_types": ["macro_briefing", "sector_rotation_report"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "strategy_lab_scout",
        "division": DIVISION_MARKET_INTELLIGENCE,
        "name": "Strategy Lab Scout",
        "purpose": "Develop, backtest, and rank paper-trading strategies. Sharpe > 1.5 target.",
        "schedule_hours": 1,
        "success_metrics": ["sharpe_ratio", "profit_factor", "max_drawdown"],
        "success_thresholds": {"sharpe_ratio": 1.5, "profit_factor": 1.3, "max_drawdown": 0.10},
        "failure_metrics": ["sharpe_below_1", "drawdown_above_15pct"],
        "optimization_targets": ["sharpe_ratio", "win_rate", "expectancy"],
        "output_types": ["strategy_report", "backtest_result", "youtube_script"],
        "evidence_required": True,
        "safe_autonomous": True,
        "note": "NO live trading — research and paper trading only",
    },
    {
        "scout_id": "volatility_scout",
        "division": DIVISION_MARKET_INTELLIGENCE,
        "name": "Volatility Scout",
        "purpose": "Track VIX, options volatility, and risk regime signals",
        "schedule_hours": 2,
        "success_metrics": ["regime_calls", "volatility_alerts"],
        "output_types": ["volatility_briefing", "risk_regime_report"],
        "evidence_required": True,
        "safe_autonomous": True,
    },

    # ── Monetization Intelligence Division ───────────────────────────────────

    {
        "scout_id": "affiliate_scout",
        "division": DIVISION_MONETIZATION_INTELLIGENCE,
        "name": "Affiliate Scout",
        "purpose": "Discover, score, and rank new affiliate programs with high ROI potential",
        "schedule_hours": 12,
        "success_metrics": ["new_programs_found", "avg_roi_score", "recommendations_created"],
        "failure_metrics": ["zero_new_programs_7_days"],
        "optimization_targets": ["roi_score", "commission_rate", "traffic_alignment"],
        "output_types": ["affiliate_opportunity", "recommendation", "newsletter_cta"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "seo_scout",
        "division": DIVISION_MONETIZATION_INTELLIGENCE,
        "name": "SEO Scout",
        "purpose": "Identify high-opportunity keywords, rising search trends, content gaps",
        "schedule_hours": 6,
        "success_metrics": ["keywords_found", "content_opportunities", "estimated_traffic"],
        "failure_metrics": ["zero_opportunities_5_days"],
        "optimization_targets": ["keyword_difficulty", "traffic_potential", "monetization_alignment"],
        "output_types": ["seo_article", "keyword_report", "content_brief"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "content_trend_scout",
        "division": DIVISION_MONETIZATION_INTELLIGENCE,
        "name": "Content Trend Scout",
        "purpose": "Monitor viral content trends on YouTube, TikTok, X. Extract Nexus-relevant angles.",
        "schedule_hours": 2,
        "success_metrics": ["trending_topics", "viral_hooks_extracted", "content_ideas"],
        "optimization_targets": ["view_potential", "engagement_score", "monetization_fit"],
        "output_types": ["tiktok_hook", "youtube_script", "x_post", "trend_report"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "funding_opportunity_scout",
        "division": DIVISION_MONETIZATION_INTELLIGENCE,
        "name": "Funding Opportunity Scout",
        "purpose": "Find small business grants, loans, credit programs, and funding intelligence",
        "schedule_hours": 24,
        "success_metrics": ["opportunities_found", "leads_generated", "consultation_requests"],
        "failure_metrics": ["zero_opportunities_14_days"],
        "optimization_targets": ["funding_amount", "approval_probability", "urgency"],
        "output_types": ["funding_report", "newsletter_section", "seo_article"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "newsletter_growth_scout",
        "division": DIVISION_MONETIZATION_INTELLIGENCE,
        "name": "Newsletter Growth Scout",
        "purpose": "Analyze newsletter growth tactics, open rates, CTR optimization, subscriber acquisition",
        "schedule_hours": 24,
        "success_metrics": ["subscriber_growth", "open_rate", "ctr", "recommendations"],
        "optimization_targets": ["subscriber_growth_rate", "open_rate", "ctr"],
        "output_types": ["growth_recommendation", "ab_test_suggestion", "newsletter_draft"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "youtube_growth_scout",
        "division": DIVISION_MONETIZATION_INTELLIGENCE,
        "name": "YouTube Growth Scout",
        "purpose": "Optimize YouTube growth: titles, thumbnails, SEO, algorithm alignment",
        "schedule_hours": 24,
        "success_metrics": ["video_ideas", "title_optimizations", "estimated_views"],
        "optimization_targets": ["click_through_rate", "watch_time", "subscriber_conversion"],
        "output_types": ["youtube_script", "title_test", "thumbnail_recommendation"],
        "evidence_required": True,
        "safe_autonomous": True,
    },
    {
        "scout_id": "revenue_consensus_engine",
        "division": DIVISION_MONETIZATION_INTELLIGENCE,
        "name": "Revenue Consensus Engine",
        "purpose": "Aggregate all monetization scout findings. Score and rank top opportunities.",
        "schedule_hours": 6,
        "success_metrics": ["opportunities_ranked", "consensus_score_variance", "roi_accuracy"],
        "output_types": ["opportunity_ranking", "executive_summary", "priority_actions"],
        "evidence_required": True,
        "safe_autonomous": True,
        "depends_on": ["affiliate_scout", "seo_scout", "content_trend_scout", "newsletter_growth_scout"],
    },
]

SCOUTS_BY_ID = {s["scout_id"]: s for s in SCOUTS}
DIVISION_SCOUTS = {
    DIVISION_MARKET_INTELLIGENCE: [s for s in SCOUTS if s["division"] == DIVISION_MARKET_INTELLIGENCE],
    DIVISION_MONETIZATION_INTELLIGENCE: [s for s in SCOUTS if s["division"] == DIVISION_MONETIZATION_INTELLIGENCE],
}


def get_scout(scout_id: str) -> dict | None:
    return SCOUTS_BY_ID.get(scout_id)


def get_division_scouts(division: str) -> list[dict]:
    return DIVISION_SCOUTS.get(division, [])


def get_due_scouts(since_hours: float = 0.5) -> list[dict]:
    """Return scouts whose schedule_hours has elapsed since last run."""
    due = []
    for scout in SCOUTS:
        flag = ROOT / "artifacts" / "scout_flags" / f"{scout['scout_id']}_last_run.json"
        if not flag.exists():
            due.append(scout)
            continue
        try:
            data = json.loads(flag.read_text())
            last_ts = datetime.fromisoformat(data.get("last_run", "2000-01-01"))
            elapsed_h = (datetime.now(timezone.utc) - last_ts.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            if elapsed_h >= scout.get("schedule_hours", 24):
                due.append(scout)
        except Exception:
            due.append(scout)
    return due


def mark_scout_run(scout_id: str, output_count: int = 0, evidence: str = "") -> None:
    flag_dir = ROOT / "artifacts" / "scout_flags"
    flag_dir.mkdir(parents=True, exist_ok=True)
    (flag_dir / f"{scout_id}_last_run.json").write_text(
        json.dumps({
            "scout_id": scout_id,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "output_count": output_count,
            "evidence": evidence,
        }, indent=2)
    )


def scout_registry_summary() -> str:
    lines = [
        "Nexus Scout Registry",
        f"  Total scouts: {len(SCOUTS)}",
        f"  Market Intelligence: {len(DIVISION_SCOUTS[DIVISION_MARKET_INTELLIGENCE])} scouts",
        f"  Monetization Intelligence: {len(DIVISION_SCOUTS[DIVISION_MONETIZATION_INTELLIGENCE])} scouts",
        "",
    ]
    for div, scouts in DIVISION_SCOUTS.items():
        lines.append(f"[{div.replace('_', ' ').title()}]")
        for s in scouts:
            lines.append(f"  {s['scout_id']:35} every {s['schedule_hours']}h → {', '.join(s['output_types'][:2])}")
        lines.append("")
    return "\n".join(lines).strip()
