"""
transcript_artifact_pipeline.py
Parses strategy summary files into structured research artifacts and upserts
them into the Supabase `research` table.

Each summary is broken into section artifacts (strategies, risk, psychology,
indicators) — one record per section per video, keyed by title so re-runs
are idempotent.
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Any

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)

STRATEGIES_DIR = Path(__file__).parent.parent.parent / "research-engine" / "strategies"

TOPIC_MAP = {
    "SMB Capital":           "trading",
    "Scarface Trades":       "trading",
    "TraderNick":            "trading",
    "No Nonsense Forex":     "trading",
    "Credit Plug":           "credit",
    "Alec Delpuech":         "credit",
    "Stedman Waiters":       "credit",
    "TechConversations":     "tech",
    "Robert's Tech Toolbox": "tech",
    "JT Automations":        "business",
    "Monica Main":           "business",
}

SECTIONS = [
    ("strategies",    r"\*\*Strategies\*\*"),
    ("risk",          r"\*\*Risk Management\*\*"),
    ("psychology",    r"\*\*Psychology\*\*"),
    ("indicators",    r"\*\*Indicators\*\*"),
    ("trade_setups",  r"\*\*Trade Setups\*\*"),
    ("bottom_line",   r"\*\*Bottom line\*\*"),
]


def _classify_topic(source: str) -> str:
    for key, topic in TOPIC_MAP.items():
        if key.lower() in source.lower():
            return topic
    return "general"


def _extract_sections(text: str) -> Dict[str, str]:
    """Split summary text into named sections."""
    result: Dict[str, str] = {}
    # Build a combined pattern to find all section boundaries
    boundaries = []
    for name, pattern in SECTIONS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            boundaries.append((m.start(), name))
    boundaries.sort()

    for i, (start, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        chunk = text[start:end].strip()
        # Remove the header line itself
        lines = chunk.split("\n", 1)
        body = lines[1].strip() if len(lines) > 1 else ""
        if body and len(body) > 30:
            result[name] = body
    return result


def _video_title(stem: str) -> str:
    """Clean up the file stem into a readable video title."""
    return stem.replace(".en.vtt", "").strip()


def publish(limit: int = 25) -> Dict[str, Any]:
    """
    Parse strategy files and upsert artifacts into the Supabase research table.
    Returns {"inserted": N, "skipped": N, "topics": {topic: count}}.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not set")

    from supabase import create_client
    sb = create_client(supabase_url, supabase_key)

    files = sorted(
        STRATEGIES_DIR.glob("*.summary"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )[:limit]

    inserted = 0
    skipped = 0
    topics: Dict[str, int] = {}

    # Build set of existing titles to avoid duplicate inserts
    try:
        existing = {r["title"] for r in (sb.table("research").select("title").execute().data or [])}
    except Exception:
        existing = set()

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            skipped += 1
            continue

        stem = f.stem
        video_title = _video_title(stem)
        source = video_title.split(" - ")[0] if " - " in video_title else "unknown"
        topic = _classify_topic(source)
        topics[topic] = topics.get(topic, 0) + 1

        sections = _extract_sections(text)
        if not sections:
            sections = {"summary": text[:3000]}

        for section_name, content in sections.items():
            artifact_title = f"[{section_name}] {video_title}"
            if artifact_title in existing:
                skipped += 1
                continue
            record = {
                "source": source,
                "title": artifact_title,
                "content": f"Topic: {topic}\nSection: {section_name}\nVideo: {video_title}\n\n{content}",
            }
            try:
                sb.table("research").insert(record).execute()
                existing.add(artifact_title)
                inserted += 1
            except Exception as e:
                logger.warning("Insert failed for %s: %s", artifact_title, e)
                skipped += 1

    logger.info("Artifact pipeline: inserted=%d skipped=%d topics=%s", inserted, skipped, topics)
    return {"inserted": inserted, "skipped": skipped, "topics": topics}
