from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from revenue_engine.revenue_foundation import load_revenue_foundation_config


ROOT = Path(__file__).resolve().parent.parent
YOUTUBE_DIR = ROOT / "youtube"
CHANNEL_CONFIG_PATH = YOUTUBE_DIR / "channel_config.json"
PILLARS_PATH = YOUTUBE_DIR / "content_pillars.json"
QUEUE_PATH = YOUTUBE_DIR / "content_queue.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_channel_config() -> dict[str, Any]:
    return _read_json(CHANNEL_CONFIG_PATH, {})


def load_content_pillars() -> dict[str, Any]:
    return _read_json(PILLARS_PATH, {"pillars": []})


def load_content_queue() -> list[dict[str, Any]]:
    data = _read_json(QUEUE_PATH, {"items": []})
    if isinstance(data, dict):
        return data.get("items") or []
    if isinstance(data, list):
        return data
    return []


def save_content_queue(items: list[dict[str, Any]]) -> None:
    _write_json(QUEUE_PATH, {"items": items})


def _slug(text: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return clean[:60] or "youtube-item"


def add_idea(pillar: str, title: str, priority: str = "medium", fmt: str = "long") -> dict[str, Any]:
    items = load_content_queue()
    item = {
        "id": f"yt-{_slug(title)}-{len(items)+1}",
        "pillar": pillar,
        "title": title,
        "format": fmt,
        "status": "idea",
        "priority": priority,
        "outline": "",
        "description": "",
        "shorts_hooks": [],
        "CTA": "",
        "affiliate_tieins": [],
        "source_links": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    items.append(item)
    save_content_queue(items)
    return item


def list_ideas(status: str | None = None) -> list[dict[str, Any]]:
    rows = load_content_queue()
    if status:
        rows = [r for r in rows if str(r.get("status") or "") == status]
    return rows


def _find_pillar(name: str) -> dict[str, Any] | None:
    pillars = load_content_pillars().get("pillars") or []
    nl = name.lower().strip()
    for p in pillars:
        if str(p.get("id") or "").lower() == nl or str(p.get("name") or "").lower() == nl:
            return p
    return None


def recommend_revenue_tieins(pillar: str) -> dict[str, Any]:
    p = _find_pillar(pillar) or {}
    rev = load_revenue_foundation_config()
    lead_magnets = [m.get("name") for m in (rev.get("lead_magnets") or [])][:4]
    mini_tools = [m.get("name") for m in (rev.get("ai_mini_tools") or [])][:4]
    affiliates = [a.get("partner") for a in (rev.get("affiliate_offers") or []) if a.get("category") in (p.get("affiliate_categories") or [])]
    return {
        "newsletter_topic": (p.get("topic_ideas") or ["Nexus operations update"])[0],
        "lead_magnet": (p.get("lead_magnets") or lead_magnets[:1] or [""])[0],
        "affiliate_recommendation": affiliates[:4] or [a.get("partner") for a in (rev.get("affiliate_offers") or [])[:3]],
        "mini_tool": (p.get("mini_tools") or mini_tools[:1] or [""])[0],
        "nexus_module_tie_in": (p.get("nexus_modules") or ["Nexus"])[0],
    }


def generate_outline(title: str, pillar: str) -> dict[str, Any]:
    p = _find_pillar(pillar) or {}
    tieins = recommend_revenue_tieins(pillar)
    outline = {
        "hook": f"Why {title} matters now",
        "sections": [
            "Problem and stakes",
            "Framework walkthrough",
            "Checklist or examples",
            "Common mistakes",
            "Action plan for next 7 days",
        ],
        "cta": p.get("cta") or "Subscribe for weekly Nexus intelligence updates.",
        "revenue_tieins": tieins,
    }
    return outline


def generate_description(title: str, pillar: str) -> str:
    cfg = load_channel_config()
    tieins = recommend_revenue_tieins(pillar)
    return (
        f"{title}\n\n"
        f"In this video, Nexus breaks down practical steps you can use today.\n"
        f"Pillar: {pillar}\n\n"
        f"Free resource: {tieins.get('lead_magnet')}\n"
        f"Newsletter: {cfg.get('newsletter_cta', '')}\n"
        f"Nexus app: {cfg.get('nexus_app_cta', '')}\n\n"
        f"Affiliate disclosure: {cfg.get('affiliate_disclosure_template', '')}"
    )


def generate_shorts(title: str) -> list[str]:
    return [
        f"If you only do one thing for {title}, do this first.",
        f"Most people miss this when they try {title}.",
        f"Steal this 30-second framework for {title}.",
    ]


def generate_upload_metadata(title: str, pillar: str) -> dict[str, Any]:
    cfg = load_channel_config()
    return {
        "title": title,
        "description": generate_description(title, pillar),
        "tags": ["nexus", "business", pillar, "ai automation", "funding", "credit"],
        "category": "Education",
        "playlist_hint": pillar,
        "default_cta": cfg.get("default_cta", ""),
        "manual_upload_only": True,
    }


def create_content_calendar() -> list[dict[str, Any]]:
    items = load_content_queue()
    planned = [r for r in items if r.get("status") in {"idea", "outlined", "scripted"}]
    calendar = []
    for idx, row in enumerate(planned[:12], start=1):
        calendar.append(
            {
                "week": idx,
                "title": row.get("title"),
                "pillar": row.get("pillar"),
                "status": row.get("status"),
            }
        )
    return calendar


def ingest_channel_link(url: str) -> dict[str, Any]:
    return {"mode": "safe_stub", "type": "channel", "url": url, "max_videos": 30, "dedup": True, "created_at": _now()}


def ingest_playlist_link(url: str) -> dict[str, Any]:
    return {"mode": "safe_stub", "type": "playlist", "url": url, "max_videos": 30, "dedup": True, "created_at": _now()}


def status() -> dict[str, Any]:
    cfg = load_channel_config()
    q = load_content_queue()
    by_status: dict[str, int] = {}
    for row in q:
        s = str(row.get("status") or "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "channel_name": cfg.get("channel_name", "Nexus YouTube"),
        "queue_total": len(q),
        "queue_status": by_status,
        "manual_upload_only": True,
    }
