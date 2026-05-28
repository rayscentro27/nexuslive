"""
youtube_intelligence_extractor.py
===================================
Extracts four intelligence categories from a YouTube source transcript or description.

Extracted categories:
  1. Content Intelligence      — hooks, pain points, viral angles, title patterns
  2. Monetization Intelligence — affiliate opportunities, product offers, lead magnets
  3. Nexus Improvement Intelligence — credit repair strategies, funding strategies
  4. Compliance Intelligence   — risk flags, guarantee language, regulatory concerns

Each run saves 4 artifact files:
  docs/reports/youtube/content_intelligence_<source_id>_<ts>.json
  docs/reports/youtube/monetization_intelligence_<source_id>_<ts>.json
  docs/reports/youtube/nexus_improvement_<source_id>_<ts>.json
  docs/reports/youtube/compliance_intelligence_<source_id>_<ts>.json

And an intelligence report (MD):
  docs/reports/youtube/youtube_intelligence_report_<source_id>_<ts>.md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "docs" / "reports" / "youtube"


class IntelligenceBundle:
    """Holds all four intelligence artifacts for one source."""

    def __init__(
        self,
        source_id: str,
        url: str,
        content: dict,
        monetization: dict,
        nexus_improvement: dict,
        compliance: dict,
        artifact_paths: list[str],
        report_path: str,
    ):
        self.source_id        = source_id
        self.url              = url
        self.content          = content
        self.monetization     = monetization
        self.nexus_improvement = nexus_improvement
        self.compliance       = compliance
        self.artifact_paths   = artifact_paths
        self.report_path      = report_path

    def has_compliance_flags(self) -> bool:
        return bool(self.compliance.get("risk_flags"))

    def to_dict(self) -> dict:
        return {
            "source_id":         self.source_id,
            "content":           self.content,
            "monetization":      self.monetization,
            "nexus_improvement": self.nexus_improvement,
            "compliance":        self.compliance,
            "artifact_paths":    self.artifact_paths,
            "report_path":       self.report_path,
        }


class YouTubeIntelligenceExtractor:

    SYSTEM = (
        "You are the Nexus intelligence analyst. Extract structured intelligence "
        "from YouTube content to help build credit repair, funding, and entrepreneurship "
        "education for the Nexus platform.\n"
        "CRITICAL: Flag ANY guarantee language or misleading income/credit claims "
        "as compliance risks. Return ONLY valid JSON matching the requested schema."
    )

    def extract(
        self,
        source_id: str,
        url: str,
        *,
        transcript: str = "",
        description: str = "",
        channel_name: str = "",
        video_title: str = "",
    ) -> IntelligenceBundle:
        """
        Extract all four intelligence categories from source material.
        Uses LLM if available, falls back to heuristic extraction.
        """
        source_text = self._build_source_text(
            transcript=transcript,
            description=description,
            channel_name=channel_name,
            video_title=video_title,
        )

        content        = self._extract_content_intelligence(source_text, video_title)
        monetization   = self._extract_monetization_intelligence(source_text)
        nexus_improve  = self._extract_nexus_improvement(source_text)
        compliance     = self._extract_compliance_intelligence(source_text)

        artifact_paths = self._save_artifacts(
            source_id, url, content, monetization, nexus_improve, compliance
        )
        report_path    = self._save_report(
            source_id, url, channel_name, video_title,
            content, monetization, nexus_improve, compliance
        )

        # Update source registry
        try:
            from lib.youtube_source_registry import _registry
            for p in artifact_paths + [report_path]:
                _registry.add_artifact(source_id, p)
            _registry.update(source_id, research_status="intelligence_extracted")
        except Exception:
            pass

        return IntelligenceBundle(
            source_id=source_id,
            url=url,
            content=content,
            monetization=monetization,
            nexus_improvement=nexus_improve,
            compliance=compliance,
            artifact_paths=artifact_paths,
            report_path=report_path,
        )

    # ── Extraction methods ─────────────────────────────────────────────────────

    def _extract_content_intelligence(self, text: str, title: str) -> dict:
        schema = {
            "hooks":              "list of 3-5 compelling opening hooks from the content",
            "pain_points":        "list of pain points the content addresses",
            "viral_angles":       "list of angles that could make this content go viral",
            "title_patterns":     "list of title formats/patterns used",
            "content_gaps":       "list of topics the content misses or under-covers",
            "audience_triggers":  "emotional/psychological triggers used",
        }
        return self._llm_extract("content_intelligence", text, schema) or {
            "hooks":             self._heuristic_hooks(title),
            "pain_points":       [],
            "viral_angles":      [],
            "title_patterns":    [title] if title else [],
            "content_gaps":      [],
            "audience_triggers": [],
        }

    def _extract_monetization_intelligence(self, text: str) -> dict:
        schema = {
            "affiliate_opportunities": "list of products/services mentioned that have affiliate programs",
            "product_offers":          "list of products/courses/services the creator sells or mentions",
            "lead_magnet_ideas":       "list of free resources that could be offered to capture leads",
            "pricing_signals":         "any prices, fees, or cost ranges mentioned",
            "nexus_offer_ideas":       "offers Nexus could create inspired by this content",
        }
        return self._llm_extract("monetization_intelligence", text, schema) or {
            "affiliate_opportunities": [],
            "product_offers":          [],
            "lead_magnet_ideas":       [],
            "pricing_signals":         [],
            "nexus_offer_ideas":       [],
        }

    def _extract_nexus_improvement(self, text: str) -> dict:
        schema = {
            "credit_repair_strategies": "specific credit repair tactics mentioned (citable)",
            "funding_strategies":       "specific funding/grant approaches mentioned",
            "platform_feature_ideas":   "features Nexus could build based on this content",
            "educational_modules":      "topics that could become Nexus learn-by-doing modules",
            "compliance_best_practices": "responsible practices mentioned in the content",
        }
        return self._llm_extract("nexus_improvement", text, schema) or {
            "credit_repair_strategies":  [],
            "funding_strategies":        [],
            "platform_feature_ideas":    [],
            "educational_modules":       [],
            "compliance_best_practices": [],
        }

    def _extract_compliance_intelligence(self, text: str) -> dict:
        schema = {
            "risk_flags":           "list of phrases/claims that could violate CROA or FTC guidelines",
            "guarantee_language":   "list of guarantee or income promise statements found",
            "misleading_claims":    "list of potentially misleading statements",
            "safe_to_reference":    "true/false — is this source safe to use in Nexus education",
            "compliance_notes":     "summary of compliance posture",
        }
        return self._llm_extract("compliance_intelligence", text, schema) or {
            "risk_flags":         self._heuristic_risk_flags(text),
            "guarantee_language": [],
            "misleading_claims":  [],
            "safe_to_reference":  len(self._heuristic_risk_flags(text)) == 0,
            "compliance_notes":   "Heuristic scan only — LLM review required for full compliance check.",
        }

    # ── LLM + Heuristic helpers ────────────────────────────────────────────────

    def _llm_extract(self, category: str, text: str, schema: dict) -> dict | None:
        try:
            import re
            from lib.content_generation_router import generate_content
            schema_lines = "\n".join(f'  "{k}": <{v}>' for k, v in schema.items())
            prompt = f"""Extract {category.replace('_', ' ')} from this YouTube source content.

Content:
---
{text[:2000]}
---

Return ONLY this JSON schema (no other text):
{{
{schema_lines}
}}"""
            result = generate_content(
                prompt=prompt, system=self.SYSTEM,
                tier="lightweight", timeout=60, max_tokens=800,
            )
            raw = result.get("response", "") if isinstance(result, dict) else str(result)
            m = re.search(r'\{.+\}', raw, re.DOTALL)
            if not m:
                return None
            return json.loads(m.group())
        except Exception:
            return None

    def _heuristic_hooks(self, title: str) -> list[str]:
        if not title:
            return []
        return [
            f"Did you know {title.lower()}?",
            f"The truth about {title.lower()}",
            f"Here's what nobody tells you about {title.lower()}",
        ]

    def _heuristic_risk_flags(self, text: str) -> list[str]:
        risky_phrases = [
            "guarantee", "guaranteed", "100% success", "always works",
            "never fails", "instant credit", "overnight results",
            "secret method", "banks hate", "loophole",
        ]
        lower = text.lower()
        return [p for p in risky_phrases if p in lower]

    def _build_source_text(
        self,
        transcript: str,
        description: str,
        channel_name: str,
        video_title: str,
    ) -> str:
        parts = []
        if video_title:
            parts.append(f"Title: {video_title}")
        if channel_name:
            parts.append(f"Channel: {channel_name}")
        if description:
            parts.append(f"Description: {description[:500]}")
        if transcript:
            parts.append(f"Transcript (excerpt): {transcript[:1500]}")
        return "\n".join(parts)

    # ── Artifact saving ────────────────────────────────────────────────────────

    def _save_artifacts(
        self,
        source_id: str,
        url: str,
        content: dict,
        monetization: dict,
        nexus_improve: dict,
        compliance: dict,
    ) -> list[str]:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        sid     = source_id[:8]
        paths   = []
        artifacts = [
            ("content_intelligence",      content),
            ("monetization_intelligence", monetization),
            ("nexus_improvement",         nexus_improve),
            ("compliance_intelligence",   compliance),
        ]
        for name, data in artifacts:
            p = REPORTS_DIR / f"{name}_{sid}_{ts}.json"
            p.write_text(json.dumps({"source_id": source_id, "url": url, **data}, indent=2))
            paths.append(str(p))
        return paths

    def _save_report(
        self,
        source_id: str,
        url: str,
        channel_name: str,
        video_title: str,
        content: dict,
        monetization: dict,
        nexus_improve: dict,
        compliance: dict,
    ) -> str:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        sid  = source_id[:8]
        path = REPORTS_DIR / f"youtube_intelligence_report_{sid}_{ts}.md"

        safe = compliance.get("safe_to_reference", True)
        flags = compliance.get("risk_flags", [])
        flag_block = "\n".join(f"- ⚠ {f}" for f in flags) if flags else "- None detected"

        report = f"""# YouTube Intelligence Report
**Source ID:** `{source_id}`
**URL:** {url}
**Channel:** {channel_name or 'N/A'}
**Title:** {video_title or 'N/A'}
**Generated:** {_now()}
**Safe to reference:** {'✅ Yes' if safe else '❌ No — compliance review required'}

---

## Content Intelligence
**Hooks:**
{chr(10).join(f'- {h}' for h in content.get('hooks', [])) or '- (none extracted)'}

**Pain Points:**
{chr(10).join(f'- {p}' for p in content.get('pain_points', [])) or '- (none extracted)'}

**Viral Angles:**
{chr(10).join(f'- {a}' for a in content.get('viral_angles', [])) or '- (none extracted)'}

---

## Monetization Intelligence
**Affiliate Opportunities:**
{chr(10).join(f'- {a}' for a in monetization.get('affiliate_opportunities', [])) or '- (none)'}

**Product Offers:**
{chr(10).join(f'- {o}' for o in monetization.get('product_offers', [])) or '- (none)'}

**Nexus Offer Ideas:**
{chr(10).join(f'- {i}' for i in monetization.get('nexus_offer_ideas', [])) or '- (none)'}

---

## Nexus Improvement Intelligence
**Credit Repair Strategies:**
{chr(10).join(f'- {s}' for s in nexus_improve.get('credit_repair_strategies', [])) or '- (none)'}

**Funding Strategies:**
{chr(10).join(f'- {s}' for s in nexus_improve.get('funding_strategies', [])) or '- (none)'}

**Platform Feature Ideas:**
{chr(10).join(f'- {f}' for f in nexus_improve.get('platform_feature_ideas', [])) or '- (none)'}

---

## Compliance Intelligence
**Risk Flags:**
{flag_block}

**Notes:** {compliance.get('compliance_notes', 'N/A')}
"""
        path.write_text(report)
        return str(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Singleton ─────────────────────────────────────────────────────────────────
_extractor = YouTubeIntelligenceExtractor()


def extract_intelligence(
    source_id: str,
    url: str,
    **kwargs,
) -> IntelligenceBundle:
    return _extractor.extract(source_id, url, **kwargs)
