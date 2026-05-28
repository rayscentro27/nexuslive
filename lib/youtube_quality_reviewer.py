"""
youtube_quality_reviewer.py
============================
Scores YouTube sources on 10 quality dimensions and assigns an actionable status.

Scoring dimensions (each 0-10):
  1.  content_relevance     — aligns with credit repair, funding, entrepreneurship
  2.  production_quality    — professional, clear audio/video, good structure
  3.  information_density   — actionable tips per minute, not filler
  4.  credibility           — cites sources, demonstrates real expertise
  5.  recency               — published within 2 years for compliance-sensitive topics
  6.  audience_alignment    — speaks to Nexus users (credit rebuilders, small biz owners)
  7.  compliance_safety     — avoids misleading claims, CROA-sensitive content
  8.  monetization_potential — hooks, offers, or lead magnets Nexus can model
  9.  uniqueness             — not rehashing basic common knowledge
  10. transcript_extractable — captions available, clear speech, extractable

Status thresholds:
  high_value          score >= 7.5
  useful_but_needs_review  5.0 <= score < 7.5
  low_quality         3.0 <= score < 5.0
  risky               compliance_safety < 4 (regardless of overall score)
  duplicate           identical channel/topic already registered
  outdated            recency < 3 (published >3 years ago on compliance topic)
  irrelevant          content_relevance < 3

Artifacts saved to: docs/reports/youtube/quality_review_<source_id>_<ts>.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT        = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "docs" / "reports" / "youtube"

DIMENSIONS = [
    "content_relevance",
    "production_quality",
    "information_density",
    "credibility",
    "recency",
    "audience_alignment",
    "compliance_safety",
    "monetization_potential",
    "uniqueness",
    "transcript_extractable",
]

QualityStatus = str  # one of the 7 values below
STATUSES = (
    "high_value",
    "useful_but_needs_review",
    "low_quality",
    "risky",
    "duplicate",
    "outdated",
    "irrelevant",
)


class QualityReview:
    def __init__(self, data: dict):
        self._data = data

    @property
    def source_id(self) -> str:
        return self._data["source_id"]

    @property
    def quality_score(self) -> float:
        return self._data["quality_score"]

    @property
    def status(self) -> QualityStatus:
        return self._data["status"]

    @property
    def artifact_path(self) -> str:
        return self._data.get("artifact_path", "")

    def to_dict(self) -> dict:
        return dict(self._data)

    def __repr__(self) -> str:
        return (
            f"QualityReview(id={self.source_id[:8]}, "
            f"score={self.quality_score:.1f}, status={self.status})"
        )


class YouTubeQualityReviewer:

    REVIEW_SYSTEM = (
        "You are a content quality evaluator for the Nexus AI platform. "
        "Your job is to score YouTube sources on 10 dimensions (each 0-10) "
        "based on their relevance to credit repair, small business funding, "
        "and entrepreneurship education. "
        "CRITICAL: Flag any content that makes guarantees about credit scores, "
        "funding approvals, or income results — mark compliance_safety < 4. "
        "Return ONLY valid JSON matching the requested schema. No prose, no markdown."
    )

    def review(
        self,
        source_id: str,
        url: str,
        *,
        channel_name: str = "",
        video_title: str = "",
        description: str = "",
        published_at: str = "",
        known_duplicates: list[str] | None = None,
        existing_registry_urls: list[str] | None = None,
    ) -> QualityReview:
        """
        Score a source and return a QualityReview. Saves artifact automatically.
        If LLM is unavailable, uses heuristic scoring.
        """
        scores = self._score(
            url=url,
            channel_name=channel_name,
            video_title=video_title,
            description=description,
            published_at=published_at,
            known_duplicates=known_duplicates or [],
        )
        status = self._classify_status(scores, url, known_duplicates or [], existing_registry_urls or [])
        overall = round(sum(scores.values()) / len(scores), 2)

        artifact = self._save_artifact(
            source_id=source_id,
            url=url,
            channel_name=channel_name,
            video_title=video_title,
            scores=scores,
            status=status,
            overall=overall,
        )

        # Update source registry
        try:
            from lib.youtube_source_registry import _registry
            _registry.update(
                source_id,
                quality_score=overall,
                status="needs_review" if status in ("risky", "useful_but_needs_review") else
                       "rejected" if status in ("low_quality", "risky", "irrelevant", "outdated") else
                       "active",
            )
            _registry.add_artifact(source_id, str(artifact))
        except Exception:
            pass

        return QualityReview({
            "source_id":     source_id,
            "url":           url,
            "channel_name":  channel_name,
            "video_title":   video_title,
            "scores":        scores,
            "quality_score": overall,
            "status":        status,
            "reviewed_at":   _now(),
            "artifact_path": str(artifact),
        })

    # ── Internals ──────────────────────────────────────────────────────────────

    def _score(
        self,
        url: str,
        channel_name: str,
        video_title: str,
        description: str,
        published_at: str,
        known_duplicates: list[str],
    ) -> dict[str, float]:
        """Score via LLM or heuristic fallback."""
        try:
            return self._score_via_llm(url, channel_name, video_title, description, published_at)
        except Exception:
            return self._score_heuristic(url, channel_name, video_title, description, published_at)

    def _score_via_llm(
        self,
        url: str,
        channel_name: str,
        video_title: str,
        description: str,
        published_at: str,
    ) -> dict[str, float]:
        from lib.content_generation_router import generate_content
        prompt = f"""Score this YouTube source on 10 quality dimensions (0-10 each).

Source:
  URL: {url}
  Channel: {channel_name or 'unknown'}
  Title: {video_title or 'unknown'}
  Description: {description[:500] or 'not provided'}
  Published: {published_at or 'unknown'}

Dimensions to score:
{chr(10).join(f'  {d}' for d in DIMENSIONS)}

Return ONLY this JSON (no other text):
{{
  "content_relevance": <0-10>,
  "production_quality": <0-10>,
  "information_density": <0-10>,
  "credibility": <0-10>,
  "recency": <0-10>,
  "audience_alignment": <0-10>,
  "compliance_safety": <0-10>,
  "monetization_potential": <0-10>,
  "uniqueness": <0-10>,
  "transcript_extractable": <0-10>
}}"""
        result = generate_content(
            prompt=prompt, system=self.REVIEW_SYSTEM,
            tier="lightweight", timeout=45, max_tokens=300,
        )
        raw = result.get("response", "") if isinstance(result, dict) else str(result)
        # Extract JSON block
        import re
        m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if not m:
            raise ValueError(f"No JSON in LLM response: {raw[:200]}")
        data = json.loads(m.group())
        # Validate all 10 keys present
        for dim in DIMENSIONS:
            if dim not in data:
                raise ValueError(f"Missing dimension: {dim}")
        return {d: float(data[d]) for d in DIMENSIONS}

    def _score_heuristic(
        self,
        url: str,
        channel_name: str,
        video_title: str,
        description: str,
        published_at: str,
    ) -> dict[str, float]:
        """Heuristic scoring when LLM unavailable."""
        text = f"{channel_name} {video_title} {description}".lower()
        credit_kw = ["credit", "score", "repair", "dispute", "collection", "fico", "credit report"]
        biz_kw    = ["funding", "business", "entrepreneur", "side hustle", "grant", "loan", "revenue"]
        risky_kw  = ["guarantee", "guaranteed", "100%", "instant", "overnight", "secret method"]

        relevance   = min(10.0, sum(2 for kw in credit_kw + biz_kw if kw in text))
        compliance  = max(0.0, 8.0 - sum(3 for kw in risky_kw if kw in text))
        recency     = 7.0  # default neutral when date unknown
        if published_at:
            try:
                pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                age_years = (datetime.now(timezone.utc) - pub).days / 365
                recency = max(0.0, 10.0 - age_years * 2)
            except Exception:
                pass

        return {
            "content_relevance":      min(10.0, relevance),
            "production_quality":     6.0,
            "information_density":    5.0,
            "credibility":            6.0,
            "recency":                recency,
            "audience_alignment":     min(10.0, relevance * 0.8),
            "compliance_safety":      compliance,
            "monetization_potential": min(10.0, relevance * 0.6),
            "uniqueness":             5.0,
            "transcript_extractable": 6.0,
        }

    def _classify_status(
        self,
        scores: dict[str, float],
        url: str,
        known_duplicates: list[str],
        existing_urls: list[str],
    ) -> QualityStatus:
        if url in known_duplicates or url in existing_urls:
            return "duplicate"
        if scores.get("compliance_safety", 10) < 4:
            return "risky"
        if scores.get("recency", 10) < 3 and scores.get("content_relevance", 10) > 5:
            return "outdated"
        if scores.get("content_relevance", 10) < 3:
            return "irrelevant"
        overall = sum(scores.values()) / len(scores)
        if overall >= 7.5:
            return "high_value"
        if overall >= 5.0:
            return "useful_but_needs_review"
        return "low_quality"

    def _save_artifact(
        self,
        source_id: str,
        url: str,
        channel_name: str,
        video_title: str,
        scores: dict[str, float],
        status: QualityStatus,
        overall: float,
    ) -> Path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"quality_review_{source_id[:8]}_{ts}.json"
        path  = REPORTS_DIR / fname
        path.write_text(json.dumps({
            "source_id":     source_id,
            "url":           url,
            "channel_name":  channel_name,
            "video_title":   video_title,
            "scores":        scores,
            "quality_score": overall,
            "status":        status,
            "reviewed_at":   _now(),
        }, indent=2))
        return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Singleton ─────────────────────────────────────────────────────────────────
_reviewer = YouTubeQualityReviewer()


def review_source(
    source_id: str,
    url: str,
    **kwargs,
) -> QualityReview:
    return _reviewer.review(source_id, url, **kwargs)
