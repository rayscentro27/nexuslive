from __future__ import annotations

import json
import os
import sys
import urllib.parse
from functools import lru_cache
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.hook_generator import generate_hooks
from scripts.prelaunch_utils import rest_select, supabase_request, table_exists


PLATFORM_CONFIG = {
    "tiktok": {
        "label": "TikTok",
        "aliases": {"tiktok", "tik tok"},
        "hook_style": "curiosity",
        "hashtags": ["#TikTokBusiness", "#Fundability", "#BusinessCredit", "#NexusAI", "#SmallBusinessTips"],
    },
    "instagram_reels": {
        "label": "Instagram Reels",
        "aliases": {"instagram", "instagram reels", "ig", "reels"},
        "hook_style": "mistake-based",
        "hashtags": ["#InstagramReels", "#FundableBusiness", "#BusinessSetup", "#NexusAI", "#EntrepreneurTips"],
    },
    "youtube_shorts": {
        "label": "YouTube Shorts",
        "aliases": {"youtube", "youtube shorts", "shorts"},
        "hook_style": "authority",
        "hashtags": ["#YouTubeShorts", "#BusinessFunding", "#CreditEducation", "#NexusAI", "#BusinessGrowth"],
    },
}

PREFERRED_CTAS = (
    "Start your funding journey with Nexus.",
    "Stop applying too early. Get fundable first.",
    "Build your business foundation with Nexus.",
    "Upload your credit report and get your roadmap.",
)

PROHIBITED_PHRASES = (
    "guarantee",
    "guaranteed",
    "guarantees",
    "guaranteeing",
    "grant approval",
    "guaranteed approval",
    "instant approval",
    "sba approval",
    "credit repair",
    "overnight funding",
    "easy money",
    "passive income",
    "six figures fast",
)


def _clean_text(value: str, fallback: str) -> str:
    cleaned = " ".join((value or "").strip().split())
    return cleaned or fallback


def _topic_seed(topic_row: dict[str, Any]) -> int:
    return sum(ord(ch) for ch in f"{topic_row.get('id', '')}{topic_row.get('slug', '')}{topic_row.get('topic', '')}")


def normalize_platform(platform: str | None) -> str | None:
    if not platform:
        return None
    raw = " ".join(str(platform).strip().lower().replace("-", " ").replace("_", " ").split())
    for key, cfg in PLATFORM_CONFIG.items():
        if raw == key.replace("_", " ") or raw == cfg["label"].lower() or raw in cfg["aliases"]:
            return key
    raise ValueError(f"Unsupported platform: {platform}")


def selected_platforms(platform: str | None = None) -> list[str]:
    normalized = normalize_platform(platform)
    return [normalized] if normalized else list(PLATFORM_CONFIG.keys())


def _pick_hook(topic: str, platform_key: str) -> str:
    style = PLATFORM_CONFIG[platform_key]["hook_style"]
    hooks = generate_hooks(topic, count=6)
    for item in hooks:
        if item.get("style") == style:
            return item.get("hook") or topic
    return hooks[0]["hook"] if hooks else topic


def _pick_cta(topic_row: dict[str, Any], platform_key: str) -> str:
    index = (_topic_seed(topic_row) + list(PLATFORM_CONFIG.keys()).index(platform_key)) % len(PREFERRED_CTAS)
    return PREFERRED_CTAS[index]


def _build_script(topic: str, theme: str, platform_label: str, cta: str) -> str:
    return (
        f"{_pick_hook(topic, normalize_platform(platform_label) or 'tiktok')}\n\n"
        f"Here is the simple version. If you are working on {topic.lower()}, do not treat funding like the first move. "
        f"Start by checking whether your business basics match what lenders and vendors expect.\n\n"
        f"Look at three things: your business identity, your documentation, and your timing. "
        f"Is your business name consistent everywhere? Does your email, website, phone, and address look professional? "
        f"Are you applying because you are ready, or just because an ad made it sound urgent?\n\n"
        f"For {platform_label}, keep the takeaway practical: fix one weak point, document the change, then review your full foundation before the next application. "
        f"That is how you build a stronger path without hype. {cta}"
    )


def _build_caption(topic: str, theme: str, cta: str) -> str:
    return (
        f"{topic} made simple. "
        f"This one breaks down a practical angle on {theme.lower()} so founders can understand what to check before moving too fast. "
        f"{cta}"
    )


def _build_compliance_notes(topic: str, theme: str) -> str:
    return (
        "Educational draft only. Manual human review required before any use. "
        "No promises about funding, approvals, credit outcomes, grants, SBA results, trading performance, or income. "
        f"Keep examples general and practical for topic '{topic}' in theme '{theme}'."
    )


def _validate_copy(variant: dict[str, Any]) -> None:
    fields = [
        variant["hook"],
        variant["script"],
        variant["caption"],
        variant["cta"],
    ]
    lowered = " ".join(fields).lower()
    found = [phrase for phrase in PROHIBITED_PHRASES if phrase in lowered]
    if found:
        raise ValueError(f"prohibited phrase(s) found: {', '.join(sorted(found))}")


def build_variant(topic_row: dict[str, Any], platform_key: str) -> dict[str, Any]:
    topic = _clean_text(topic_row.get("topic", ""), "business funding timing")
    theme = _clean_text(topic_row.get("theme", ""), "business readiness")
    platform_label = PLATFORM_CONFIG[platform_key]["label"]
    cta = _pick_cta(topic_row, platform_key)
    variant = {
        "topic_id": topic_row["id"],
        "campaign_id": topic_row.get("campaign_id"),
        "platform": platform_label,
        "platform_key": platform_key,
        "hook": _pick_hook(topic, platform_key),
        "script": _build_script(topic, theme, platform_label, cta),
        "caption": _build_caption(topic, theme, cta),
        "hashtags": PLATFORM_CONFIG[platform_key]["hashtags"],
        "cta": cta,
        "compliance_notes": _build_compliance_notes(topic, theme),
        "status": "pending_review",
        "created_by": "content_variant_generator",
        "variant_type": "short_form",
        "topic": topic,
        "theme": theme,
        "manual_review_required": True,
    }
    _validate_copy(variant)
    return variant


def fetch_topics(limit: int | None = None) -> list[dict[str, Any]]:
    query = (
        "content_topics?select=id,campaign_id,slug,topic,theme,status,target_stage"
        "&order=created_at.asc"
    )
    if limit:
        query += f"&limit={int(limit)}"
    rows = rest_select(query) or []
    return [row for row in rows if row.get("id")]


@lru_cache(maxsize=None)
def _column_supported(table: str, column: str) -> bool:
    try:
        rest_select(f"{table}?select={urllib.parse.quote(column, safe='')}&limit=0")
        return True
    except Exception:
        return False


def _find_existing_variant(topic_id: str, platform_label: str) -> dict[str, Any] | None:
    topic_id_q = urllib.parse.quote(topic_id, safe="")
    platform_q = urllib.parse.quote(platform_label, safe="")
    rows = rest_select(
        f"content_variants?select=id,status,platform,topic_id&topic_id=eq.{topic_id_q}&platform=eq.{platform_q}&limit=1"
    ) or []
    return rows[0] if rows else None


def _variant_insert_body(variant: dict[str, Any]) -> dict[str, Any]:
    caption_draft = variant["caption"]
    compliance_notes = variant["compliance_notes"]
    body = {
        "topic_id": variant["topic_id"],
        "platform": variant["platform"],
        "variant_type": variant["variant_type"],
        "hook_draft": variant["hook"],
        "script_draft": variant["script"],
        "caption_draft": caption_draft,
        "compliance_notes": compliance_notes,
        "status": variant["status"],
    }
    optional_fields = {
        "campaign_id": variant.get("campaign_id"),
        "hashtags": variant.get("hashtags"),
        "cta": variant.get("cta"),
        "created_by": variant.get("created_by"),
    }
    for column, value in optional_fields.items():
        if value is not None and _column_supported("content_variants", column):
            body[column] = value
    if "hashtags" not in body:
        body["caption_draft"] = f"{caption_draft}\n\nHashtags: {' '.join(variant['hashtags'])}"
    meta_lines = []
    if "campaign_id" not in body and variant.get("campaign_id"):
        meta_lines.append(f"Campaign ID: {variant['campaign_id']}")
    if "cta" not in body:
        meta_lines.append(f"CTA: {variant['cta']}")
    if "created_by" not in body:
        meta_lines.append(f"Created by: {variant['created_by']}")
    if meta_lines:
        body["compliance_notes"] = f"{compliance_notes}\n" + "\n".join(meta_lines)
    return body


def _save_variant(variant: dict[str, Any]) -> dict[str, Any]:
    rows, _ = supabase_request(
        "content_variants",
        method="POST",
        body=_variant_insert_body(variant),
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


def _preview_row(variant: dict[str, Any], *, existing: bool = False) -> dict[str, Any]:
    return {
        "topic_id": variant["topic_id"],
        "campaign_id": variant.get("campaign_id"),
        "platform": variant["platform"],
        "hook": variant["hook"],
        "script": variant["script"],
        "caption": variant["caption"],
        "hashtags": variant["hashtags"],
        "cta": variant["cta"],
        "compliance_notes": variant["compliance_notes"],
        "status": variant["status"],
        "created_by": variant["created_by"],
        "duplicate": existing,
    }


def generate_content_variants(
    *,
    limit: int | None = None,
    dry_run: bool = True,
    platform: str | None = None,
) -> dict[str, Any]:
    platforms = selected_platforms(platform)
    topics = fetch_topics(limit=limit)
    created: list[dict[str, Any]] = []
    preview: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    duplicates_skipped = 0

    for topic_row in topics:
        for platform_key in platforms:
            try:
                variant = build_variant(topic_row, platform_key)
                existing = _find_existing_variant(variant["topic_id"], variant["platform"])
                if existing:
                    duplicates_skipped += 1
                    if dry_run and len(preview) < 18:
                        preview.append(_preview_row(variant, existing=True))
                    continue
                if dry_run:
                    if len(preview) < 18:
                        preview.append(_preview_row(variant))
                    continue
                saved = _save_variant(variant)
                if not saved.get("id"):
                    raise RuntimeError("variant write returned empty response")
                _ensure_approval(saved["id"])
                created.append({
                    "id": saved["id"],
                    "topic_id": variant["topic_id"],
                    "campaign_id": variant.get("campaign_id"),
                    "platform": variant["platform"],
                    "status": saved.get("status", variant["status"]),
                    "created_by": variant["created_by"],
                })
            except Exception as exc:
                failures.append({
                    "topic_id": topic_row.get("id"),
                    "campaign_id": topic_row.get("campaign_id"),
                    "topic": topic_row.get("topic"),
                    "platform": PLATFORM_CONFIG[platform_key]["label"],
                    "error": str(exc),
                })

    return {
        "dry_run": dry_run,
        "platforms": [PLATFORM_CONFIG[key]["label"] for key in platforms],
        "topics_processed": len(topics),
        "variants_created": len(created),
        "duplicates_skipped": duplicates_skipped,
        "generation_failures": failures,
        "preview_variants": preview,
        "created_variants": created[:10],
        "review_locations": [
            "Control Center -> GROWTH tab -> Recent Content Variants",
            "Supabase: public.content_variants",
            "Supabase: public.content_approvals",
        ],
        "posted_count": 0,
        "scheduled_count": 0,
        "messages_sent_count": 0,
        "requires_human_review": True,
        "draft_only": True,
    }


def variants_as_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2)
