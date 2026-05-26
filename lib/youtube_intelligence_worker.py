"""
YouTube Intelligence Worker
=============================
Extracts intelligence from registered YouTube sources.

Pipeline per source:
  1. fetch video IDs (channel → latest N videos, video URL → single)
  2. pull transcript via youtube-transcript-api
  3. fallback: pull metadata + description via yt-dlp
  4. extract intelligence via LLM (OpenRouter deepseek/deepseek-chat)
  5. apply recency + tier quality weighting
  6. save extraction to Supabase source_extractions table
  7. generate scout findings → worker_recommendations
  8. feed opportunity rankings via consensus engine

No publishing. No trading. Research + intelligence generation only.
Evidence: every extraction saves a Supabase row_id.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("YouTubeIntelligenceWorker")
ROOT = Path(__file__).resolve().parent.parent

# ── Config loader ─────────────────────────────────────────────────────────────

_SOURCES_CACHE: dict | None = None


def _load_sources() -> dict:
    global _SOURCES_CACHE
    if _SOURCES_CACHE:
        return _SOURCES_CACHE
    try:
        import yaml
        src_file = ROOT / "config" / "nexus_sources.yaml"
        _SOURCES_CACHE = yaml.safe_load(src_file.read_text())
    except Exception as exc:
        logger.warning("Could not load nexus_sources.yaml: %s", exc)
        _SOURCES_CACHE = {}
    return _SOURCES_CACHE


def get_all_sources() -> list[dict]:
    cfg = _load_sources()
    return (cfg.get("monetization_sources") or []) + (cfg.get("market_intelligence_sources") or [])


def get_sources_by_scout(scout_id: str) -> list[dict]:
    return [s for s in get_all_sources() if s.get("scout") == scout_id]


def get_sources_by_division(division: str) -> list[dict]:
    return [s for s in get_all_sources() if s.get("division") == division]


# ── Recency + tier weighting ──────────────────────────────────────────────────

def _recency_weight(publish_date: str | None) -> float:
    cfg = _load_sources()
    rw = cfg.get("recency_weighting", {})
    if not publish_date:
        return rw.get("age_31_90_days", 0.70)
    try:
        pub = datetime.fromisoformat(str(publish_date).replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - pub).days
        if age_days <= 7:
            return rw.get("age_0_7_days", 1.0)
        if age_days <= 30:
            return rw.get("age_8_30_days", 0.85)
        if age_days <= 90:
            return rw.get("age_31_90_days", 0.70)
        if age_days <= 180:
            return rw.get("age_91_180_days", 0.50)
        if age_days <= 365:
            return rw.get("age_181_365_days", 0.35)
        return rw.get("age_over_1_year", 0.20)
    except Exception:
        return 0.60


def _tier_multiplier(tier: str) -> float:
    cfg = _load_sources()
    return cfg.get("tier_multipliers", {}).get(tier.upper(), 0.60)


def apply_weights(base_confidence: float, tier: str, publish_date: str | None) -> float:
    return min(100.0, round(base_confidence * _tier_multiplier(tier) * _recency_weight(publish_date), 1))


# ── Video ID extraction ───────────────────────────────────────────────────────

def _extract_video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _get_channel_video_ids(channel_url: str, max_videos: int = 5) -> list[dict]:
    """Get latest N video IDs + titles from a channel using yt-dlp."""
    try:
        import yt_dlp
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "playlistend": max_videos,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get("entries") or []
            return [
                {"id": e.get("id", ""), "title": e.get("title", ""), "url": e.get("url", "")}
                for e in entries[:max_videos] if e.get("id")
            ]
    except Exception as exc:
        logger.debug("Channel video fetch failed for %s: %s", channel_url, exc)
        return []


# ── Transcript fetching ───────────────────────────────────────────────────────

def _fetch_transcript(video_id: str, max_words: int = 1200) -> str:
    """Fetch YouTube transcript. Returns cleaned text up to max_words."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        chunks = list(api.fetch(video_id))
        text = " ".join(c.text for c in chunks)
        text = re.sub(r"\[.*?\]", "", text)          # remove [Music], [Applause]
        text = re.sub(r"\s+", " ", text).strip()
        words = text.split()
        return " ".join(words[:max_words])
    except Exception as exc:
        logger.debug("Transcript fetch failed for %s: %s", video_id, exc)
        return ""


def _fetch_metadata(video_id: str) -> dict:
    """Fetch video metadata + description via yt-dlp as transcript fallback."""
    try:
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return {
                "title": info.get("title", ""),
                "channel": info.get("channel", ""),
                "description": (info.get("description") or "")[:800],
                "upload_date": info.get("upload_date", ""),
                "view_count": info.get("view_count", 0),
                "duration": info.get("duration", 0),
                "tags": info.get("tags", [])[:10],
            }
    except Exception as exc:
        logger.debug("Metadata fetch failed for %s: %s", video_id, exc)
        return {}


def _parse_upload_date(upload_date: str) -> str | None:
    """Convert 'YYYYMMDD' to ISO date string."""
    if not upload_date or len(upload_date) < 8:
        return None
    try:
        return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    except Exception:
        return None


# ── LLM extraction ────────────────────────────────────────────────────────────

EXTRACTION_PROMPTS = {
    "monetization_intelligence": """You are a monetization intelligence analyst for Nexus AI.

Analyze this YouTube video content and extract structured intelligence.
Focus ONLY on actionable monetization intelligence.

Video: {title}
Channel: {channel}
Content: {content}

Extract and return JSON with these fields:
{{
  "summary": "2-3 sentence summary of core monetization insight",
  "affiliate_opportunities": ["specific affiliate programs or products mentioned"],
  "seo_opportunities": ["specific keyword opportunities or content gaps identified"],
  "content_ideas": ["specific content ideas with titles"],
  "cta_strategies": ["specific CTA approaches that could work for Nexus"],
  "newsletter_opportunities": ["newsletter topic ideas or growth tactics"],
  "recurring_revenue_systems": ["subscription/recurring revenue models described"],
  "automation_ideas": ["specific automation workflows that could generate income"],
  "key_tools_mentioned": ["software/tools mentioned with use case"],
  "actionable_insight": "the single most actionable insight for Nexus to implement this week",
  "confidence_score": 70,
  "tags": ["3-5 relevant tags"]
}}

Return ONLY valid JSON. No markdown, no explanation.""",

    "market_intelligence": """You are a market intelligence analyst for Nexus AI.

Analyze this YouTube video content and extract structured market intelligence.
Focus ONLY on research-grade market insights. NO investment advice.

Video: {title}
Channel: {channel}
Content: {content}

Extract and return JSON with these fields:
{{
  "summary": "2-3 sentence summary of key market intelligence",
  "macro_insights": ["macro economic signals or themes identified"],
  "institutional_behavior": ["institutional positioning or behavior signals"],
  "volatility_expectations": ["volatility analysis or VIX-related insights"],
  "strategy_logic": ["specific strategy concepts or frameworks described"],
  "market_regime_signals": ["regime identification signals mentioned"],
  "risk_management_concepts": ["risk management approaches discussed"],
  "consensus_signals": ["consensus view or contrarian signals"],
  "paper_trading_setups": ["specific setup criteria for paper trading research"],
  "key_concepts": ["technical concepts or terms worth researching"],
  "actionable_insight": "the single most research-worthy insight for paper trading strategy development",
  "confidence_score": 70,
  "tags": ["3-5 relevant tags"]
}}

Return ONLY valid JSON. No markdown, no explanation."""
}


def _extract_with_llm(content: str, title: str, channel: str, division: str) -> dict:
    """Run LLM extraction on transcript/content. Returns structured dict."""
    prompt_template = EXTRACTION_PROMPTS.get(division, EXTRACTION_PROMPTS["monetization_intelligence"])
    prompt = prompt_template.format(
        title=title[:200],
        channel=channel[:100],
        content=content[:3000],
    )

    # Try OpenRouter
    try:
        import urllib.request
        base_url = (os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/")
        model = os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-chat"
        key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
        raw = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return json.loads(raw)
    except Exception as exc:
        logger.debug("LLM extraction failed: %s", exc)

    # Fallback: keyword-based extraction
    return _keyword_extraction_fallback(content, title, division)


def _keyword_extraction_fallback(content: str, title: str, division: str) -> dict:
    """Rule-based fallback extraction when LLM is unavailable."""
    text = (title + " " + content).lower()

    if division == "market_intelligence":
        return {
            "summary": f"Market intelligence from: {title[:80]}",
            "macro_insights": _extract_phrases(text, ["macro", "fed", "rate", "inflation", "gdp", "recession"]),
            "institutional_behavior": _extract_phrases(text, ["institutional", "smart money", "whale", "flow", "positioning"]),
            "volatility_expectations": _extract_phrases(text, ["vix", "volatility", "fear", "greed", "options"]),
            "strategy_logic": _extract_phrases(text, ["strategy", "setup", "entry", "exit", "confluence"]),
            "market_regime_signals": _extract_phrases(text, ["regime", "trend", "range", "bearish", "bullish"]),
            "risk_management_concepts": _extract_phrases(text, ["risk", "drawdown", "stop loss", "position size"]),
            "consensus_signals": _extract_phrases(text, ["consensus", "majority", "contrarian", "positioning"]),
            "paper_trading_setups": [],
            "key_concepts": [],
            "actionable_insight": f"Review full video for strategy intel: {title[:60]}",
            "confidence_score": 40,
            "tags": ["market_intelligence", "research"],
        }

    return {
        "summary": f"Monetization intel from: {title[:80]}",
        "affiliate_opportunities": _extract_phrases(text, ["affiliate", "commission", "partner", "referral"]),
        "seo_opportunities": _extract_phrases(text, ["seo", "keyword", "rank", "traffic", "search"]),
        "content_ideas": [f"Content idea from: {title[:60]}"],
        "cta_strategies": _extract_phrases(text, ["cta", "subscribe", "call to action", "click", "sign up"]),
        "newsletter_opportunities": _extract_phrases(text, ["newsletter", "email list", "subscribers", "open rate"]),
        "recurring_revenue_systems": _extract_phrases(text, ["recurring", "subscription", "membership", "monthly"]),
        "automation_ideas": _extract_phrases(text, ["automate", "automation", "workflow", "system", "passive"]),
        "key_tools_mentioned": _extract_phrases(text, ["tool", "software", "platform", "app", "saas"]),
        "actionable_insight": f"Review video for monetization tactics: {title[:60]}",
        "confidence_score": 35,
        "tags": ["monetization", "content"],
    }


def _extract_phrases(text: str, keywords: list[str], context_words: int = 4) -> list[str]:
    """Extract short phrases around keywords."""
    found = []
    words = text.split()
    for i, word in enumerate(words):
        if any(kw in word for kw in keywords):
            start = max(0, i - 2)
            end = min(len(words), i + context_words)
            phrase = " ".join(words[start:end]).strip()
            if len(phrase) > 8 and phrase not in found:
                found.append(phrase[:80])
        if len(found) >= 3:
            break
    return found


# ── Supabase persistence ──────────────────────────────────────────────────────

def _save_extraction(
    source: dict,
    video_id: str,
    video_title: str,
    publish_date: str | None,
    extraction: dict,
    raw_content_len: int,
    confidence: float,
) -> str | None:
    """Save extraction to source_extractions table. Returns row ID."""
    try:
        import urllib.request
        url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
        if not url or not key:
            return None
        payload = {
            "source_id": source["source_id"],
            "division": source["division"],
            "scout_id": source["scout"],
            "video_id": video_id,
            "video_title": video_title[:200],
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "publish_date": publish_date,
            "tier": source.get("tier", "B"),
            "extraction_data": extraction,
            "summary": str(extraction.get("summary", ""))[:400],
            "confidence_score": confidence,
            "raw_content_chars": raw_content_len,
            "tags": source.get("tags", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(payload, default=str).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/source_extractions",
            data=data,
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json",
                     "Prefer": "return=representation"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if isinstance(result, list) and result:
                return str(result[0].get("id", ""))
            return None
    except Exception as exc:
        logger.debug("Save extraction failed: %s", exc)
        return None


def _save_scout_finding(source: dict, extraction: dict, confidence: float, evidence_ref: str = "") -> bool:
    """Save key insights as scout_outputs for consensus engine."""
    try:
        import urllib.request
        url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
        if not url or not key:
            return False

        summary = str(extraction.get("summary", ""))
        actionable = str(extraction.get("actionable_insight", ""))

        payload = {
            "scout_id": source.get("scout", "unknown_scout"),
            "division": source.get("division", ""),
            "output_type": "intelligence_extraction",
            "title": f"[{source.get('tier','B')}] {source.get('name','?')[:80]}",
            "summary": f"{summary} | Insight: {actionable}"[:600],
            "raw_data": {
                "source_id": source["source_id"],
                "extraction_goals": source.get("extraction_goals", []),
                "key_findings": {
                    k: v for k, v in extraction.items()
                    if isinstance(v, list) and v and k not in ("tags",)
                },
                "actionable_insight": actionable,
                "confidence_score": confidence,
            },
            "confidence": confidence,
            "priority": "high" if confidence >= 70 else "medium" if confidence >= 50 else "low",
            "evidence_ref": evidence_ref,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(payload, default=str).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/scout_outputs",
            data=data,
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8):
            return True
    except Exception:
        return False


def _save_recommendation(source: dict, extraction: dict, confidence: float) -> bool:
    """Save actionable intelligence as worker_recommendation."""
    insight = str(extraction.get("actionable_insight", ""))
    if not insight:
        return False
    try:
        import urllib.request
        url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
        if not url or not key:
            return False
        rec_type = "market_intelligence" if "market" in source.get("division", "") else "monetization_opportunity"
        payload = {
            "worker_id": f"youtube_intel_{source.get('scout','scout')}",
            "recommendation_type": rec_type,
            "title": f"{source.get('name','?')[:60]}: {insight[:80]}",
            "summary": str(extraction.get("summary", ""))[:300],
            "priority": "high" if confidence >= 70 else "medium",
            "action_required": confidence >= 65,
            "context": json.dumps({
                "source_id": source["source_id"],
                "tier": source.get("tier", "B"),
                "confidence": confidence,
                "division": source.get("division"),
            }),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(payload, default=str).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/worker_recommendations",
            data=data,
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8):
            return True
    except Exception:
        return False


# ── Last-run tracking ─────────────────────────────────────────────────────────

def _source_flag(source_id: str) -> Path:
    d = ROOT / "artifacts" / "source_flags"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{source_id}.json"


def _source_due(source: dict) -> bool:
    flag = _source_flag(source["source_id"])
    if not flag.exists():
        return True
    try:
        data = json.loads(flag.read_text())
        last = datetime.fromisoformat(data["last_run"].replace("Z", "+00:00"))
        elapsed_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return elapsed_h >= source.get("frequency_hours", 168)
    except Exception:
        return True


def _mark_source_run(source_id: str, videos_processed: int, findings: int, evidence_refs: list[str]) -> None:
    _source_flag(source_id).write_text(json.dumps({
        "source_id": source_id,
        "last_run": datetime.now(timezone.utc).isoformat(),
        "videos_processed": videos_processed,
        "findings": findings,
        "evidence_refs": evidence_refs[:10],
    }, indent=2))


# ── Main processing ───────────────────────────────────────────────────────────

def process_source(source: dict, force: bool = False) -> dict:
    """
    Full pipeline for one source:
    fetch → transcript → extract → weight → save → recommend
    Returns summary dict with evidence.
    """
    source_id = source["source_id"]
    if not force and not _source_due(source):
        return {"source_id": source_id, "skipped": True, "reason": "not_due"}

    logger.info("Processing source: %s", source_id)

    src_type = source.get("type", "video")
    videos: list[dict] = []

    if src_type == "channel":
        max_v = source.get("max_videos", 5)
        videos = _get_channel_video_ids(source["url"], max_videos=max_v)
        if not videos:
            logger.warning("No videos found for channel: %s", source["url"])
    else:
        vid_id = _extract_video_id(source["url"])
        if vid_id:
            videos = [{"id": vid_id, "title": source.get("name", ""), "url": source["url"]}]

    if not videos:
        return {"source_id": source_id, "skipped": True, "reason": "no_videos_found"}

    total_findings = 0
    evidence_refs: list[str] = []
    processed = 0

    for video in videos[:6]:
        vid_id = video["id"]
        vid_title = video.get("title") or source.get("name", "")

        # 1. Try transcript
        transcript = _fetch_transcript(vid_id)
        content = transcript

        # 2. Fallback to metadata + description
        meta = {}
        if not content:
            meta = _fetch_metadata(vid_id)
            content = (meta.get("description") or "")
            if not content:
                logger.debug("No content for video %s — skipping", vid_id)
                continue
        else:
            meta = _fetch_metadata(vid_id)

        publish_date = _parse_upload_date(meta.get("upload_date", ""))
        channel_name = meta.get("channel", "") or source.get("name", "")
        title = meta.get("title", "") or vid_title or source.get("name", "")

        # 3. Extract intelligence
        extraction = _extract_with_llm(content, title, channel_name, source["division"])

        # 4. Apply weights
        raw_confidence = float(extraction.get("confidence_score", 60))
        confidence = apply_weights(raw_confidence, source.get("tier", "B"), publish_date)

        # 5. Save extraction to Supabase
        row_id = _save_extraction(
            source, vid_id, title, publish_date, extraction,
            len(content), confidence,
        )
        if row_id:
            evidence_refs.append(f"source_extractions:{row_id}")

        # 6. Save scout finding
        _save_scout_finding(source, extraction, confidence, evidence_ref=row_id or "")

        # 7. Save recommendation if high confidence
        if confidence >= 50:
            _save_recommendation(source, extraction, confidence)
            total_findings += 1

        processed += 1
        time.sleep(0.5)  # rate limit courtesy

    _mark_source_run(source_id, processed, total_findings, evidence_refs)

    return {
        "source_id": source_id,
        "division": source["division"],
        "scout": source["scout"],
        "tier": source.get("tier", "B"),
        "videos_processed": processed,
        "findings": total_findings,
        "evidence_refs": evidence_refs,
        "skipped": False,
    }


def run_due_sources(division: str | None = None, limit: int = 10, force: bool = False) -> dict:
    """Run all due sources. Optionally filter by division. Returns summary."""
    all_sources = get_all_sources()
    if division:
        all_sources = [s for s in all_sources if s.get("division") == division]

    due = [s for s in all_sources if force or _source_due(s)][:limit]

    if not due:
        return {"total_due": 0, "processed": 0, "total_findings": 0, "results": []}

    results = []
    total_findings = 0
    for source in due:
        result = process_source(source, force=force)
        results.append(result)
        total_findings += result.get("findings", 0)
        logger.info("  %s: %d findings", result["source_id"], result.get("findings", 0))

    return {
        "total_due": len(due),
        "processed": len([r for r in results if not r.get("skipped")]),
        "total_findings": total_findings,
        "evidence_count": sum(len(r.get("evidence_refs", [])) for r in results),
        "results": results,
    }


def daily_intelligence_summary() -> str:
    """Generate a daily intelligence summary from recent source extractions."""
    try:
        from scripts.prelaunch_utils import rest_select
        from datetime import timedelta
        yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        rows = rest_select(
            f"source_extractions?select=source_id,division,scout_id,video_title,summary,confidence_score,created_at"
            f"&created_at=gte.{yesterday}&order=confidence_score.desc&limit=20",
            timeout=10,
        ) or []
    except Exception:
        rows = []

    if not rows:
        return "No source extractions in the last 24 hours. Run `nexus intelligence run` to extract."

    lines = [
        f"YouTube Intelligence Summary — Last 24h ({len(rows)} extractions)",
        "",
    ]

    # Group by division
    mono = [r for r in rows if "monetization" in (r.get("division") or "")]
    market = [r for r in rows if "market" in (r.get("division") or "")]

    if mono:
        lines.append("MONETIZATION INTELLIGENCE:")
        for r in mono[:5]:
            conf = r.get("confidence_score", 0)
            lines.append(f"  [{conf:.0f}] {r.get('video_title','?')[:60]}")
            lines.append(f"       {str(r.get('summary',''))[:120]}")

    if market:
        lines.append("\nMARKET INTELLIGENCE:")
        for r in market[:4]:
            conf = r.get("confidence_score", 0)
            lines.append(f"  [{conf:.0f}] {r.get('video_title','?')[:60]}")
            lines.append(f"       {str(r.get('summary',''))[:120]}")

    lines.append(f"\nRun `nexus intelligence run` to process new sources.")
    return "\n".join(lines)


def source_registry_summary() -> str:
    """Show all registered sources with status."""
    all_sources = get_all_sources()
    mono = [s for s in all_sources if s.get("division") == "monetization_intelligence"]
    market = [s for s in all_sources if s.get("division") == "market_intelligence"]

    lines = [
        f"Nexus Source Registry ({len(all_sources)} total)",
        f"  Monetization Intelligence: {len(mono)} sources",
        f"  Market Intelligence: {len(market)} sources",
        "",
    ]

    for div_name, sources in [("MONETIZATION", mono), ("MARKET INTELLIGENCE", market)]:
        lines.append(f"[{div_name}]")
        for s in sources:
            due_marker = "⏰" if _source_due(s) else "✓ "
            lines.append(
                f"  {due_marker} {s['source_id']:40} [{s.get('tier','?')}] "
                f"every {s.get('frequency_hours','?')}h → {s.get('scout','?')}"
            )
        lines.append("")

    return "\n".join(lines).strip()
