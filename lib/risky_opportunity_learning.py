"""
risky_opportunity_learning.py — Nexus Risky Opportunity Learning Engine
========================================================================
Hermes learns from risky opportunities instead of only rejecting them.

For every risky opportunity, analyzes:
  1. What it is / why it looked attractive
  2. What made it risky (and which risk category)
  3. What Nexus can safely extract
  4. Safer reframe, education angle, content angle, monetization path
  5. Recommended disposition: rejected, watchlist, safe_reframe_available,
     education_only, internal_test_only, monetization_candidate_with_guardrails

Artifacts:
  docs/reports/risky_opportunities/risky_opportunity_analysis_<ts>.md
  docs/reports/risky_opportunities/risky_opportunity_analysis_<ts>.json
  docs/reports/risky_opportunities/risk_learning_log.json

Usage:
    from lib.risky_opportunity_learning import RiskyOpportunityEngine
    result = RiskyOpportunityEngine().analyze(
        opportunity="Automated live trading bot selling signals.",
        source="ray_manual",
    )
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT      = Path(__file__).resolve().parent.parent
RISK_DIR  = ROOT / "docs" / "reports" / "risky_opportunities"
LOG_PATH  = RISK_DIR / "risk_learning_log.json"

RISK_CATEGORIES = [
    "legal", "financial", "compliance", "reputational", "technical",
    "operational", "health", "platform", "cost", "fraud", "data_privacy",
]

DISPOSITIONS = {
    "rejected":                           "Too risky in any form — do not pursue",
    "watchlist":                          "Monitor for safer implementation; no action yet",
    "safe_reframe_available":             "Core idea is valid; reframe removes the risk",
    "education_only":                     "Can be taught about but never implemented live",
    "internal_test_only":                 "Paper/demo/sandbox testing only — no live deployment",
    "monetization_candidate_with_guardrails": "Revenue path exists after compliance guardrails added",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _llm(prompt: str, system: str = "", tier: str = "reasoning", timeout: int = 90) -> str:
    try:
        from lib.content_generation_router import generate_content
        r = generate_content(prompt=prompt, system=system, tier=tier, timeout=timeout, max_tokens=3000)
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


def _load_log() -> list[dict]:
    if LOG_PATH.exists():
        try:
            return json.loads(LOG_PATH.read_text())
        except Exception:
            pass
    return []


def _append_log(entry: dict) -> None:
    log = _load_log()
    log.append(entry)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2, default=str))


class RiskyOpportunityEngine:

    SYSTEM = (
        "You are the Nexus risk analysis AI. "
        "Your job is to extract safe value from risky ideas — "
        "not to kill ideas, but to find what's reusable, teachable, or monetizable after guardrails. "
        "Always think: what can Nexus safely do here? "
        "Output only valid JSON."
    )

    def analyze(
        self,
        opportunity: str,
        source: str = "unknown",
        context: str = "",
    ) -> dict:
        """
        Analyze a risky opportunity and produce a structured learning artifact.

        Returns dict with full analysis + artifact paths.
        """
        record_id = f"risk_{_ts()}_{uuid.uuid4().hex[:6]}"

        prompt = f"""Analyze this opportunity for Nexus (an AI business finance / education platform):

Opportunity: {opportunity}
Source: {source}
Context: {context or 'None provided'}

Nexus sells: membership, funding readiness reviews, credit education, business setup guides, affiliate products, newsletter, faceless YouTube, paper-trading strategy education.

Answer ALL questions:
1. What is the opportunity and why does it look attractive?
2. What makes it risky? Name the specific risk category from: {RISK_CATEGORIES}
3. Can Nexus safely extract anything useful? What specifically?
4. What is a safer version of this idea?
5. Can it become education content? What title/angle?
6. Can it become monetizable content? What offer/CTA?
7. Can it improve the Nexus system or workflows?
8. Can it become a monetization path WITH guardrails? What are those guardrails?
9. Disposition: one of {list(DISPOSITIONS.keys())}
10. Does this require Ray's approval before any action?
11. What is the extracted lesson — what should Hermes remember about this class of opportunity?

Return JSON:
{{
  "opportunity": "brief name for this opportunity",
  "why_attractive": "...",
  "risk_category": "one from the list",
  "risk_reason": "specific explanation",
  "extracted_lesson": "what Hermes should remember",
  "safer_alternative": "concrete safer version",
  "education_angle": "title and angle for educational content, or null",
  "content_possibility": "content type + hook + CTA, or null",
  "system_improvement": "how it could improve Nexus, or null",
  "monetization_path": "specific revenue path with guardrails, or null",
  "disposition": "one of the valid dispositions",
  "requires_ray_approval": true/false,
  "hermes_recommendation": "what Hermes recommends doing right now (one paragraph)"
}}"""

        raw    = _llm(prompt, system=self.SYSTEM, tier="reasoning")
        parsed = _parse_json(raw, {})

        if not isinstance(parsed, dict) or "risk_reason" not in parsed:
            # Minimal fallback
            parsed = {
                "opportunity":         opportunity[:100],
                "why_attractive":      "Not analyzed — LLM unavailable",
                "risk_category":       "unknown",
                "risk_reason":         "LLM analysis failed",
                "extracted_lesson":    "Analyze manually",
                "safer_alternative":   "",
                "education_angle":     None,
                "content_possibility": None,
                "system_improvement":  None,
                "monetization_path":   None,
                "disposition":         "watchlist",
                "requires_ray_approval": True,
                "hermes_recommendation": "Manual review needed — LLM unavailable",
            }

        record = {
            "id":                    record_id,
            "created":               _now(),
            "source":                source,
            "raw_opportunity":       opportunity,
            **{k: parsed.get(k, "") for k in [
                "opportunity", "why_attractive", "risk_category", "risk_reason",
                "extracted_lesson", "safer_alternative", "education_angle",
                "content_possibility", "system_improvement", "monetization_path",
                "disposition", "requires_ray_approval", "hermes_recommendation",
            ]},
        }

        ts   = _ts()
        slug = re.sub(r"[^a-z0-9]+", "_", opportunity.lower())[:35]

        # Save JSON
        json_path = _save(RISK_DIR / f"risky_opportunity_analysis_{ts}.json",
                          json.dumps(record, indent=2, default=str))
        record["json_path"] = str(json_path)

        # Save Markdown
        md   = self._render_md(record)
        md_path = _save(RISK_DIR / f"risky_opportunity_analysis_{ts}.md", md)
        record["md_path"] = str(md_path)

        # Append to log
        _append_log({
            "id":          record_id,
            "opportunity": record["opportunity"],
            "risk_category": record["risk_category"],
            "disposition": record["disposition"],
            "created":     record["created"],
        })

        return record

    def _render_md(self, r: dict) -> str:
        disp       = r.get("disposition", "unknown")
        disp_label = DISPOSITIONS.get(disp, disp)
        emoji_map  = {
            "rejected": "🚫",
            "watchlist": "👁️",
            "safe_reframe_available": "♻️",
            "education_only": "🎓",
            "internal_test_only": "🧪",
            "monetization_candidate_with_guardrails": "💰",
        }
        emoji = emoji_map.get(disp, "⚠️")
        lines = [
            f"# {emoji} Risky Opportunity Analysis",
            f"*ID: {r['id']} | {r['created']}*\n",
            f"**Opportunity:** {r['opportunity']}",
            f"**Source:** {r.get('source', 'unknown')}",
            f"**Risk Category:** `{r.get('risk_category', '?')}`",
            f"**Disposition:** `{disp}` — {disp_label}",
            f"**Requires Ray Approval:** {'YES ⚠️' if r.get('requires_ray_approval') else 'No'}\n",
            "## Why It Looked Attractive",
            r.get("why_attractive", ""),
            "\n## What Made It Risky",
            r.get("risk_reason", ""),
            "\n## Extracted Lesson",
            f"> {r.get('extracted_lesson', '')}",
            "\n## Safer Alternative",
            r.get("safer_alternative", "None identified"),
        ]
        if r.get("education_angle"):
            lines += ["\n## Education Angle", r["education_angle"]]
        if r.get("content_possibility"):
            lines += ["\n## Content Possibility", r["content_possibility"]]
        if r.get("system_improvement"):
            lines += ["\n## System Improvement", r["system_improvement"]]
        if r.get("monetization_path"):
            lines += ["\n## Monetization Path (with guardrails)", r["monetization_path"]]
        lines += ["\n## Hermes Recommendation", r.get("hermes_recommendation", "")]
        return "\n".join(lines)

    def get_log(self) -> list[dict]:
        return _load_log()

    def get_by_disposition(self, disposition: str) -> list[dict]:
        return [e for e in _load_log() if e.get("disposition") == disposition]
