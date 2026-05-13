from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, parse_qs
import re


_CATEGORY_ALIASES = {
    "business": "businessopps",
    "business_setup": "businessopps",
    "opportunities": "businessopps",
    "opportunity": "businessopps",
    "grant": "grants",
}

_CATEGORY_OWNER = {
    "trading": "trading_intelligence",
    "businessopps": "business_opportunities",
    "funding": "funding_intelligence",
    "grants": "grants_research",
    "credit": "credit_research",
    "marketing": "marketing_intelligence",
    "automation": "operations",
}


def normalize_category(raw: str) -> str:
    k = (raw or "general").strip().lower().replace("-", "_")
    return _CATEGORY_ALIASES.get(k, k)


def owner_for_category(category: str) -> str:
    return _CATEGORY_OWNER.get(normalize_category(category), "operations")


def normalize_source_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    p = urlparse(u)
    scheme = (p.scheme or "https").lower()
    netloc = (p.netloc or "").lower()
    path = (p.path or "").rstrip("/")
    if "youtu.be" in netloc:
        vid = path.strip("/")
        return f"https://www.youtube.com/watch?v={vid}" if vid else "https://www.youtube.com"
    if "youtube.com" in netloc:
        q = parse_qs(p.query)
        if path == "/watch" and q.get("v"):
            return f"https://www.youtube.com/watch?v={q['v'][0]}"
    query = p.query if "youtube.com/watch" not in (netloc + path) else ""
    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized = f"{normalized}?{query}"
    return normalized


def source_metadata(url: str) -> dict[str, str]:
    n = normalize_source_url(url)
    p = urlparse(n)
    host = (p.netloc or "").lower()
    domain = host.replace("www.", "")
    source_type = "youtube" if "youtube.com" in domain else "website"
    channel_name = ""
    website_name = ""
    if source_type == "youtube":
        m = re.search(r"youtube\.com/@([a-z0-9_.-]+)", n.lower())
        if m:
            channel_name = m.group(1)
        elif "nitrotrades" in n.lower():
            channel_name = "nitrotrades"
    else:
        website_name = domain.split(":", 1)[0]
    return {
        "source_url": n,
        "source_type": source_type,
        "domain": domain,
        "channel_name": channel_name,
        "website_name": website_name,
    }


def build_searchable_tags(category: str, source_type: str, transcript: str, title: str) -> list[str]:
    text = f"{title} {transcript}".lower()
    tags = [normalize_category(category), source_type]
    concept_map = {
        "liquidity_sweep": ["liquidity sweep", "sweep"],
        "session_timing": ["session timing", "new york session", "ny session", "london session"],
        "silver_bullet": ["silver bullet", "ict"],
        "market_structure": ["market structure", "ms", "bos", "choch"],
        "displacement": ["displacement"],
        "risk_management": ["risk", "drawdown", "stop loss", "position size"],
    }
    for tag, keys in concept_map.items():
        if any(k in text for k in keys):
            tags.append(tag)
    out: list[str] = []
    for t in tags:
        if t and t not in out:
            out.append(t)
    return out[:16]


def transcript_state(transcript: str, reason: str) -> str:
    if transcript:
        return "ready"
    if reason == "transcript_unavailable":
        return "needs_transcript"
    return "failed"


def quality_score(summary: str, transcript: str, source_type: str = "website") -> int:
    s = (summary or "").lower()
    t = (transcript or "").lower()
    score = 40
    if len(transcript) > 600:
        score += 14
    if len(transcript) > 1500:
        score += 8
    if any(k in t for k in ["risk", "drawdown", "stop", "position size"]):
        score += 10
    if any(k in s for k in ["how", "framework", "step", "process", "example"]):
        score += 10
    if any(k in t for k in ["guaranteed", "no risk", "100% win"]):
        score -= 18
    if source_type == "youtube":
        score += 4
    return max(25, min(score, 95))


def trust_score(transcript: str, title: str) -> int:
    text = f"{title} {transcript}".lower()
    score = 50
    if any(k in text for k in ["risk", "stop", "drawdown", "loss"]):
        score += 15
    if any(k in text for k in ["checklist", "rules", "journal", "review"]):
        score += 12
    if any(k in text for k in ["guaranteed", "secret formula", "overnight millionaire", "no effort"]):
        score -= 25
    return max(10, min(score, 95))


def build_ingestion_snapshot(transcript_rows: list[dict[str, Any]], knowledge_rows: list[dict[str, Any]]) -> dict[str, Any]:
    tq_status = Counter(str(r.get("status") or "unknown") for r in transcript_rows)
    source_types = Counter(str(r.get("source_type") or "unknown") for r in transcript_rows)
    k_status = Counter(str(r.get("status") or "unknown") for r in knowledge_rows)
    latest_sources = []
    for r in transcript_rows[:8]:
        src = r.get("source_url") or ""
        if src and src not in latest_sources:
            latest_sources.append(src)
    transcripts_ready = int(tq_status.get("ready", 0))
    failures = int(tq_status.get("failed", 0))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "transcript_queue_total": len(transcript_rows),
        "transcript_queue_status": dict(tq_status),
        "source_type_summary": dict(source_types),
        "proposed_count": int(k_status.get("proposed", 0)),
        "approved_count": int(k_status.get("approved", 0)),
        "rejected_count": int(k_status.get("rejected", 0)),
        "latest_sources": latest_sources,
        "transcript_available_count": transcripts_ready,
        "ingestion_failure_count": failures,
    }
