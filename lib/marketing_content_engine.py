from __future__ import annotations

from typing import Any

from lib.growth_support import audit_payload, safe_insert


PLATFORMS = ("tiktok", "instagram_reels", "youtube_shorts")


def build_content_brief(topic: str, campaign: str, platform: str, angle: str = "") -> dict[str, Any]:
    platform = platform if platform in PLATFORMS else "tiktok"
    return {
        "platform": platform,
        "campaign": campaign,
        "topic": topic,
        "angle": angle or "educational",
        "status": "draft_review",
        "manual_posting_required": True,
        "notes": "Draft only. No auto-posting.",
    }


def save_learning_note(note: str, topic_id: str | None = None, variant_id: str | None = None, created_by: str = "growth_engine") -> dict:
    return safe_insert(
        "content_learning_notes",
        audit_payload(
            "save_learning_note",
            {
                "topic_id": topic_id,
                "variant_id": variant_id,
                "note_type": "learning",
                "note": note,
                "created_by": created_by,
            },
        ),
    )
