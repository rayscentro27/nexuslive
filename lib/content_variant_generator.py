from __future__ import annotations

import json
import os
import sys
import urllib.parse
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.hook_generator import generate_hooks
from scripts.prelaunch_utils import rest_select, supabase_request, table_exists


PLATFORM_CONFIG = {
    "tiktok": {
        "label": "TikTok",
        "cta": "Comment READY if you want the next step broken down simply.",
        "hashtags": ["#BusinessCredit", "#FundableBusiness", "#NexusAI", "#EntrepreneurTips", "#MoneyEducation"],
    },
    "instagram_reels": {
        "label": "Instagram Reels",
        "cta": "Save this and send it to the business owner who is applying too early.",
        "hashtags": ["#BusinessFunding", "#BusinessSetup", "#Fundability", "#SmallBusinessTips", "#NexusGrowth"],
    },
    "youtube_shorts": {
        "label": "YouTube Shorts",
        "cta": "Subscribe for more step-by-step business funding education without hype.",
        "hashtags": ["#YouTubeShorts", "#BusinessCredit101", "#FundingTips", "#EntrepreneurEducation", "#NexusAI"],
    },
}

HOOK_STYLE_BY_PLATFORM = {
    "tiktok": "curiosity",
    "instagram_reels": "mistake-based",
    "youtube_shorts": "authority",
}


def _clean_topic(topic: str) -> str:
    return " ".join((topic or "").strip().split()) or "business funding timing"


def _pick_hook(topic: str, platform: str) -> str:
    style = HOOK_STYLE_BY_PLATFORM.get(platform, "curiosity")
    hooks = generate_hooks(topic, count=6)
    for item in hooks:
        if item.get("style") == style:
            return item.get("hook") or topic
    return hooks[0]["hook"] if hooks else topic


def _build_script(topic: str, theme: str, platform: str) -> str:
    label = PLATFORM_CONFIG[platform]["label"]
    return (
        f"{_pick_hook(topic, platform)}\n\n"
        f"If you are working on {topic.lower()}, slow down for a second. "
        f"A lot of people think one quick fix solves it, but the real issue is usually the foundation.\n\n"
        f"Start with the basics: make sure your business identity is complete, your profile is consistent, "
        f"and your timing makes sense before you apply. That matters more than hype, shortcuts, or copying what someone posted online.\n\n"
        f"For {label}, keep this simple: show one mistake, explain one fix, and give one practical next step. "
        f"In this case, the next step is to review {theme.lower()} before moving into any application or funding move.\n\n"
        f"The goal is not to promise results. The goal is to help people become more prepared, more fundable, and more informed."
    )


def _build_caption(topic: str, platform: str) -> str:
    label = PLATFORM_CONFIG[platform]["label"]
    return (
        f"{label} draft: {topic}. "
        "Keep it educational, practical, and easy to follow. "
        "This is for review only and should stay in manual posting mode."
    )


def _build_compliance_notes(topic: str, theme: str, platform: str) -> str:
    hashtags = " ".join(PLATFORM_CONFIG[platform]["hashtags"])
    cta = PLATFORM_CONFIG[platform]["cta"]
    return (
        "No guarantees about funding, credit repair, grants, SBA approvals, trading gains, or income.\n"
        "Avoid urgency language that implies guaranteed outcomes.\n"
        f"Theme: {theme or 'general education'}\n"
        f"CTA: {cta}\n"
        f"Hashtags: {hashtags}"
    )


def build_variant(topic_row: dict[str, Any], platform: str) -> dict[str, Any]:
    topic = _clean_topic(topic_row.get("topic", ""))
    theme = (topic_row.get("theme") or "business readiness").strip()
    return {
        "topic_id": topic_row["id"],
        "platform": platform,
        "variant_type": "short_form",
        "hook_draft": _pick_hook(topic, platform),
        "script_draft": _build_script(topic, theme, platform),
        "caption_draft": _build_caption(topic, platform),
        "compliance_notes": _build_compliance_notes(topic, theme, platform),
        "status": "draft_review",
        "hashtags": PLATFORM_CONFIG[platform]["hashtags"],
        "cta": PLATFORM_CONFIG[platform]["cta"],
        "topic": topic,
        "theme": theme,
    }


def fetch_topics(limit: int | None = None) -> list[dict[str, Any]]:
    query = "content_topics?select=id,slug,topic,theme,status&order=created_at.asc"
    if limit:
        query += f"&limit={int(limit)}"
    rows = rest_select(query) or []
    return [row for row in rows if row.get("id")]


def _find_existing_variant(topic_id: str, platform: str) -> dict[str, Any] | None:
    topic_id_q = urllib.parse.quote(topic_id, safe="")
    platform_q = urllib.parse.quote(platform, safe="")
    rows = rest_select(
        f"content_variants?select=id,status&topic_id=eq.{topic_id_q}&platform=eq.{platform_q}&limit=1"
    ) or []
    return rows[0] if rows else None


def _save_variant(variant: dict[str, Any]) -> dict[str, Any]:
    existing = _find_existing_variant(variant["topic_id"], variant["platform"])
    body = {
        "topic_id": variant["topic_id"],
        "platform": variant["platform"],
        "variant_type": variant["variant_type"],
        "hook_draft": variant["hook_draft"],
        "script_draft": variant["script_draft"],
        "caption_draft": (
            f"{variant['caption_draft']}\n\n"
            f"CTA: {variant['cta']}\n"
            f"Hashtags: {' '.join(variant['hashtags'])}"
        ),
        "compliance_notes": variant["compliance_notes"],
        "status": variant["status"],
    }
    if existing:
        rows, _ = supabase_request(
            f"content_variants?id=eq.{urllib.parse.quote(existing['id'], safe='')}",
            method="PATCH",
            body=body,
            prefer="return=representation",
        )
        return (rows or [None])[0] or {}
    rows, _ = supabase_request(
        "content_variants",
        method="POST",
        body=body,
        prefer="return=representation",
    )
    return (rows or [None])[0] or {}


def _ensure_approval(variant_id: str) -> None:
    if not table_exists("content_approvals"):
        return
    rows = rest_select(
        f"content_approvals?select=id,decision&variant_id=eq.{urllib.parse.quote(variant_id, safe='')}&limit=1"
    ) or []
    if rows:
        return
    supabase_request(
        "content_approvals",
        method="POST",
        body={
            "variant_id": variant_id,
            "approval_type": "content_review",
            "decision": "pending",
        },
        prefer="return=representation",
    )


def generate_content_variants(*, limit: int | None = None, dry_run: bool = True) -> dict[str, Any]:
    topics = fetch_topics(limit=limit)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for topic_row in topics:
        for platform in PLATFORM_CONFIG:
            try:
                variant = build_variant(topic_row, platform)
                if dry_run:
                    results.append({
                        "topic_id": topic_row["id"],
                        "topic": topic_row.get("topic"),
                        "platform": platform,
                        "status": "draft_review",
                        "hook": variant["hook_draft"],
                        "script": variant["script_draft"],
                        "caption": variant["caption_draft"],
                        "hashtags": variant["hashtags"],
                        "cta": variant["cta"],
                        "compliance_notes": variant["compliance_notes"],
                    })
                    continue
                saved = _save_variant(variant)
                if not saved.get("id"):
                    raise RuntimeError("variant write returned empty response")
                _ensure_approval(saved["id"])
                results.append({
                    "id": saved["id"],
                    "topic_id": topic_row["id"],
                    "topic": topic_row.get("topic"),
                    "platform": platform,
                    "status": saved.get("status", "draft_review"),
                })
            except Exception as exc:
                failures.append({
                    "topic_id": topic_row.get("id"),
                    "topic": topic_row.get("topic"),
                    "platform": platform,
                    "error": str(exc),
                })

    return {
        "dry_run": dry_run,
        "topics_processed": len(topics),
        "variants_created": len(results),
        "failures": failures,
        "results": results,
        "review_locations": [
            "Control Center → GROWTH tab",
            "Supabase table: content_variants",
            "Supabase table: content_approvals",
        ],
        "posted_live": False,
        "scheduled_live": False,
    }


def variants_as_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2)
