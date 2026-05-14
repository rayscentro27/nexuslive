"""
playlist_ingest_worker.py — YouTube playlist-based knowledge ingestion.

Supports:
- Curated YouTube playlists (by playlist ID)
- Source trust scoring per channel
- Duplicate detection before inserting transcript_queue rows
- Topic clustering using nexus_semantic_concepts
- Latest-video-first ingestion order
- Status tracking written to transcript_queue

Safety:
- PLAYLIST_INGEST_WRITES_ENABLED=true required for writes
- Max videos per run capped by PLAYLIST_MAX_VIDEOS_PER_RUN
- Never auto-approves knowledge — all records require admin review
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .env_loader import load_nexus_env
from .nexus_semantic_concepts import get_related_concepts, source_trust_score

load_nexus_env()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
WRITES_ENABLED = os.getenv("PLAYLIST_INGEST_WRITES_ENABLED", "false").lower() == "true"
MAX_VIDEOS = int(os.getenv("PLAYLIST_MAX_VIDEOS_PER_RUN", "10"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _headers(prefer: str = "") -> dict:
    h = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _supabase_get(table: str, params: dict) -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/{table}?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers=_headers())
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.warning("supabase GET %s: %s", table, exc)
        return []


def _supabase_post(table: str, payload: dict) -> dict | None:
    if not WRITES_ENABLED:
        logger.info("[DRY] would insert into %s: %s", table, str(payload)[:80])
        return {"dry_run": True, "id": "dry-" + hashlib.md5(json.dumps(payload).encode()).hexdigest()[:8]}
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=_headers("return=representation"), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result[0] if isinstance(result, list) else result
    except Exception as exc:
        logger.error("supabase POST %s: %s", table, exc)
        return None


# ── Playlist metadata registry ────────────────────────────────────────────────

CURATED_PLAYLISTS: list[dict] = [
    {
        "id": "ICT_silver_bullet",
        "name": "ICT Silver Bullet Strategy",
        "playlist_url": "https://www.youtube.com/@InnerCircleTrader",
        "channel": "InnerCircleTrader",
        "domain": "trading",
        "topic_cluster": ["silver bullet", "ict", "fair value gap", "liquidity sweep"],
        "trust_score": 78,
        "max_videos": 5,
    },
    {
        "id": "nexus_grants_research",
        "name": "Small Business Grants Research",
        "playlist_url": "https://www.youtube.com/@HelloAlice",
        "channel": "HelloAlice",
        "domain": "grants",
        "topic_cluster": ["hello alice", "small business grant", "sba grant"],
        "trust_score": 82,
        "max_videos": 5,
    },
    {
        "id": "business_credit_building",
        "name": "Business Credit Building",
        "playlist_url": "https://www.youtube.com/",
        "channel": "CreditEducation",
        "domain": "credit",
        "topic_cluster": ["business credit", "paydex score", "net 30 vendor", "tradeline"],
        "trust_score": 70,
        "max_videos": 5,
    },
    {
        "id": "ai_automation_opportunities",
        "name": "AI Automation Business Opportunities",
        "playlist_url": "https://www.youtube.com/",
        "channel": "AIBusiness",
        "domain": "business",
        "topic_cluster": ["ai automation", "ai affiliate", "agency model"],
        "trust_score": 65,
        "max_videos": 5,
    },
]


def _video_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_duplicate(source_url: str) -> bool:
    """Check if this URL is already in transcript_queue."""
    existing = _supabase_get("transcript_queue", {
        "select": "id",
        "source_url": f"eq.{source_url}",
        "limit": "1",
    })
    return len(existing) > 0


def _ingest_video(video: dict, playlist: dict) -> dict:
    """
    Ingest a single video into transcript_queue.
    Returns result dict with status.
    """
    url = video.get("url", "")
    title = video.get("title", "Untitled")

    if not url:
        return {"status": "skipped", "reason": "no_url"}

    if _is_duplicate(url):
        return {"status": "duplicate", "url": url, "title": title}

    domain = playlist["domain"]
    related = get_related_concepts(title + " " + " ".join(playlist["topic_cluster"]), domain=domain)
    trust = playlist.get("trust_score", source_trust_score(url))

    payload = {
        "title":            title,
        "source_url":       url,
        "domain":           domain,
        "status":           "needs_transcript",
        "channel_name":     playlist.get("channel", "unknown"),
        "playlist_id":      playlist["id"],
        "playlist_name":    playlist["name"],
        "trust_score":      trust,
        "topic_cluster":    playlist["topic_cluster"],
        "related_concepts": related[:5],
        "created_at":       _now(),
        "metadata": {
            "playlist_id":    playlist["id"],
            "video_hash":     _video_hash(url),
            "channel":        playlist.get("channel"),
            "trust_score":    trust,
        },
    }

    result = _supabase_post("transcript_queue", payload)
    if result:
        return {"status": "inserted", "url": url, "title": title, "id": result.get("id")}
    return {"status": "error", "url": url, "title": title}


def ingest_playlist(playlist_id: str, videos: list[dict] | None = None) -> dict:
    """
    Ingest videos from a registered playlist.

    Args:
        playlist_id: ID from CURATED_PLAYLISTS
        videos: Optional list of {'url': str, 'title': str} dicts.
                If None, runs in dry-run simulation mode.

    Returns:
        Summary dict: total, inserted, duplicates, errors
    """
    playlist = next((p for p in CURATED_PLAYLISTS if p["id"] == playlist_id), None)
    if not playlist:
        return {"error": f"Playlist ID '{playlist_id}' not found in registry"}

    if videos is None:
        logger.info("ingest_playlist %s: no video list provided — simulation only", playlist_id)
        return {
            "playlist_id": playlist_id,
            "name": playlist["name"],
            "status": "no_videos_provided",
            "writes_enabled": WRITES_ENABLED,
            "message": (
                "Provide a list of {'url': str, 'title': str} dicts to ingest. "
                "Or run YouTube scraping adapter to fetch the playlist automatically."
            ),
        }

    max_v = min(len(videos), playlist.get("max_videos", MAX_VIDEOS), MAX_VIDEOS)
    results = {"inserted": 0, "duplicates": 0, "errors": 0, "skipped": 0, "items": []}

    for video in videos[:max_v]:
        res = _ingest_video(video, playlist)
        results["items"].append(res)
        if res["status"] == "inserted":
            results["inserted"] += 1
        elif res["status"] == "duplicate":
            results["duplicates"] += 1
        elif res["status"] == "error":
            results["errors"] += 1
        else:
            results["skipped"] += 1

    logger.info(
        "playlist_ingest %s: inserted=%d duplicates=%d errors=%d writes_enabled=%s",
        playlist_id, results["inserted"], results["duplicates"], results["errors"], WRITES_ENABLED,
    )
    return {
        "playlist_id":   playlist_id,
        "name":          playlist["name"],
        "domain":        playlist["domain"],
        "total_provided": len(videos),
        "processed":     max_v,
        "inserted":      results["inserted"],
        "duplicates":    results["duplicates"],
        "errors":        results["errors"],
        "writes_enabled": WRITES_ENABLED,
    }


def list_playlists() -> list[dict]:
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "domain": p["domain"],
            "channel": p.get("channel", ""),
            "trust_score": p.get("trust_score", 50),
            "topic_cluster": p["topic_cluster"],
        }
        for p in CURATED_PLAYLISTS
    ]


def get_ingestion_status(domain: str | None = None, limit: int = 20) -> list[dict]:
    """Return recent transcript_queue items, optionally filtered by domain."""
    params: dict = {
        "select": "id,title,domain,status,created_at,channel_name,playlist_id,trust_score",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    if domain:
        params["domain"] = f"eq.{domain}"
    return _supabase_get("transcript_queue", params)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Registered playlists:")
    for p in list_playlists():
        print(f"  [{p['domain']}] {p['name']} (trust: {p['trust_score']}) — {p['channel']}")

    print("\nRecent ingestion status:")
    for item in get_ingestion_status(limit=5):
        print(f"  [{item.get('status')}] {item.get('title', 'untitled')} ({item.get('domain')})")
