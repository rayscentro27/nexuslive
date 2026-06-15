"""
monetization_operating_engine.py — Nexus Monetization Operating Engine
=======================================================================
Turns existing Nexus knowledge into ranked revenue paths with
30-day plans, required assets, and compliance checks.

Focus areas:
  1. Membership/subscription
  2. Funding readiness reviews
  3. Business setup guidance
  4. Credit readiness education
  5. Grant readiness support
  6. Business opportunity education
  7. Affiliate offers
  8. Faceless content channels
  9. Newsletters
  10. Netlify landing pages/funnels
  11. Trading education/paper strategy reports
  12. AI automation education

Artifacts:
  docs/reports/monetization/monetization_operating_report_<ts>.md
  docs/reports/monetization/monetization_rankings_<ts>.json
  docs/reports/monetization/30_day_revenue_plan_<ts>.md

Usage:
    from lib.monetization_operating_engine import MonetizationOperatingEngine
    result = MonetizationOperatingEngine().run()
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT       = Path(__file__).resolve().parent.parent
MONO_DIR   = ROOT / "docs" / "reports" / "monetization"

NEXUS_FOCUS_AREAS = [
    "nexus_membership_subscription",
    "funding_readiness_review",
    "business_setup_guidance",
    "credit_readiness_education",
    "grant_readiness_support",
    "business_opportunity_education",
    "affiliate_offers",
    "faceless_content_youtube",
    "newsletter",
    "netlify_landing_page_funnel",
    "trading_education_paper_strategy",
    "ai_automation_education",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _llm(prompt: str, system: str = "", tier: str = "reasoning", timeout: int = 120) -> str:
    try:
        from lib.content_generation_router import generate_content
        r = generate_content(prompt=prompt, system=system, tier=tier, timeout=timeout, max_tokens=4000)
        return r.get("response", "") if isinstance(r, dict) else str(r)
    except Exception as exc:
        return f"[LLM_ERROR: {exc}]"


def _parse_json(text: str, fallback: Any = None) -> Any:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _save(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _query_existing_assets() -> dict:
    """Quick audit of what Nexus assets already exist."""
    checks = {
        "content_agents":         (ROOT / "lib" / "content_agents.py").exists(),
        "content_pipeline":       (ROOT / "lib" / "content_pipeline.py").exists(),
        "vibe_trading_adapter":   (ROOT / "integrations" / "vibe_trading" / "vibe_trading_adapter.py").exists(),
        "discord_notifier":       (ROOT / "lib" / "discord_notifier.py").exists(),
        "daily_content_engine":   (ROOT / "lib" / "daily_content_engine.py").exists(),
        "content_generation_router": (ROOT / "lib" / "content_generation_router.py").exists(),
        "docs_content":           (ROOT / "docs" / "content").exists(),
        "research_briefs":        any((ROOT / "docs" / "content" / "research_briefs").glob("*.md")),
        "approval_packets":       any((ROOT / "docs" / "content" / "approval_packets").glob("*.json")),
        "youtube_scripts":        any((ROOT / "docs" / "content" / "youtube_scripts").glob("*.md")),
        "newsletters":            any((ROOT / "docs" / "content" / "newsletters").glob("*.md")),
    }
    return {k: "present" if v else "missing" for k, v in checks.items()}


class MonetizationOperatingEngine:

    SYSTEM = (
        "You are the Nexus monetization strategist. "
        "Your job is to rank revenue paths by speed to money, low cost, and Nexus fit. "
        "Be specific about price points, platforms, and CTAs. "
        "Reject vague ideas — every opportunity must have a specific offer, price, and distribution channel. "
        "Output only valid JSON."
    )

    def run(self, focus: list[str] | None = None) -> dict:
        """
        Run the monetization analysis and produce ranked opportunities + 30-day plan.
        """
        ts     = _ts()
        run_id = f"mono_{ts}_{uuid.uuid4().hex[:6]}"
        focus  = focus or NEXUS_FOCUS_AREAS

        existing = _query_existing_assets()

        prompt = f"""Rank monetization opportunities for Nexus — an AI platform helping small businesses
get funded, fix their credit, and build sustainable businesses.

Existing Nexus assets:
{json.dumps(existing, indent=2)}

Current capabilities:
- 7-agent content pipeline (research → hooks → draft → edit → CTA → approval → Discord)
- Paper trading backtester (education-only)
- Discord notification (CEO, Content, Ops channels)
- Supabase database for tracking outputs
- Hermes AI operator (Ollama local LLM via Telegram/CLI)
- OpenRouter LLM routing (deepseek-r1, deepseek-chat)
- Netlify frontend deployment capability
- Email/newsletter infrastructure (Beehiiv setup in progress)
- Credit repair + funding readiness knowledge base

Focus areas to evaluate: {focus}

For each opportunity, provide:
{{
  "name": "...",
  "target_audience": "...",
  "pain_point": "...",
  "offer": "specific product/service with price",
  "revenue_model": "one-time / subscription / affiliate / ad-revenue / etc",
  "price_range": "$X - $Y / month or one-time",
  "content_angle": "what content drives traffic to this offer",
  "funnel_angle": "how prospects go from discovery to payment",
  "required_assets": ["list of what must be built or bought"],
  "cost_to_launch": "free / <$50/mo / <$200/mo",
  "speed_to_revenue": "days | weeks | months",
  "confidence_score": 1-10,
  "compliance_risk": "low | medium | high",
  "compliance_notes": "any legal/financial disclaimer requirements",
  "next_autonomous_step": "what Nexus/Hermes can do RIGHT NOW without Ray",
  "requires_ray_approval": ["list what Ray must approve before launch"]
}}

Return JSON:
{{
  "opportunities": [ ... (all evaluated) ],
  "top_5_ranked": ["name1", "name2", ...],
  "fastest_to_revenue": "name",
  "lowest_cost": "name",
  "highest_confidence": "name",
  "thirty_day_plan": {{
    "week_1": ["action 1", "action 2"],
    "week_2": ["action 1", "action 2"],
    "week_3": ["action 1", "action 2"],
    "week_4": ["action 1", "action 2"],
    "target_revenue": "$X",
    "key_milestones": ["milestone 1", ...]
  }}
}}"""

        raw    = _llm(prompt, system=self.SYSTEM, tier="reasoning")
        parsed = _parse_json(raw, {})

        opps  = parsed.get("opportunities", []) if isinstance(parsed, dict) else []
        plan  = parsed.get("thirty_day_plan", {}) if isinstance(parsed, dict) else {}
        top5  = parsed.get("top_5_ranked", []) if isinstance(parsed, dict) else []

        result = {
            "run_id":             run_id,
            "created":            _now(),
            "opportunities":      opps,
            "top_5_ranked":       top5,
            "fastest_to_revenue": parsed.get("fastest_to_revenue", "") if isinstance(parsed, dict) else "",
            "lowest_cost":        parsed.get("lowest_cost", "") if isinstance(parsed, dict) else "",
            "highest_confidence": parsed.get("highest_confidence", "") if isinstance(parsed, dict) else "",
            "thirty_day_plan":    plan,
            "existing_assets":    existing,
            "artifacts":          {},
        }

        # Save JSON
        json_path = _save(
            MONO_DIR / f"monetization_rankings_{ts}.json",
            json.dumps(result, indent=2, default=str),
        )
        result["artifacts"]["rankings_json"] = str(json_path)

        # Save operating report
        report_md = self._render_report(result)
        report_path = _save(MONO_DIR / f"monetization_operating_report_{ts}.md", report_md)
        result["artifacts"]["report_md"] = str(report_path)

        # Save 30-day plan
        plan_md = self._render_plan(plan, result)
        plan_path = _save(MONO_DIR / f"30_day_revenue_plan_{ts}.md", plan_md)
        result["artifacts"]["plan_md"] = str(plan_path)

        return result

    def _render_report(self, r: dict) -> str:
        lines = [
            f"# Nexus Monetization Operating Report",
            f"*Run ID: {r['run_id']} | {r['created'][:10]}*\n",
            f"**Fastest to Revenue:** {r.get('fastest_to_revenue', 'N/A')}",
            f"**Lowest Cost:** {r.get('lowest_cost', 'N/A')}",
            f"**Highest Confidence:** {r.get('highest_confidence', 'N/A')}\n",
            "## Top 5 Opportunities Ranked\n",
        ]
        for i, name in enumerate(r.get("top_5_ranked", []), 1):
            lines.append(f"{i}. **{name}**")
        lines.append("\n## All Opportunities\n")
        for opp in r.get("opportunities", []):
            score = opp.get("confidence_score", 0)
            speed = opp.get("speed_to_revenue", "?")
            cost  = opp.get("cost_to_launch", "?")
            risk  = opp.get("compliance_risk", "?")
            lines.append(f"### {opp.get('name', 'Unknown')} — Confidence: {score}/10")
            lines.append(f"**Offer:** {opp.get('offer', '')} | **Price:** {opp.get('price_range', '')}")
            lines.append(f"**Speed:** {speed} | **Cost:** {cost} | **Compliance risk:** {risk}")
            lines.append(f"**Next autonomous step:** {opp.get('next_autonomous_step', '')}")
            lines.append(f"**Requires Ray approval for:** {', '.join(opp.get('requires_ray_approval', []))}")
            lines.append("")
        return "\n".join(lines)

    def _render_plan(self, plan: dict, context: dict) -> str:
        lines = [
            f"# 30-Day Nexus Revenue Plan",
            f"*Generated: {context['created'][:10]}*\n",
            f"**Target Revenue:** {plan.get('target_revenue', 'TBD')}\n",
        ]
        for wk in ["week_1", "week_2", "week_3", "week_4"]:
            lines.append(f"## {wk.replace('_', ' ').title()}")
            for action in plan.get(wk, []):
                lines.append(f"- {action}")
            lines.append("")
        lines.append("## Key Milestones\n")
        for m in plan.get("key_milestones", []):
            lines.append(f"- {m}")
        return "\n".join(lines)
