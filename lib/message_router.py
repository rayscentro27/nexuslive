from __future__ import annotations

import os

from lib.comment_responder import generate_comment_reply
from lib.dm_funnel import build_dm_draft, save_dm_draft
from lib.growth_support import safe_insert

FACEBOOK_MESSENGER_ENABLED = os.getenv("FACEBOOK_MESSENGER_ENABLED", "true").lower() == "true"
INSTAGRAM_DM_ENABLED = os.getenv("INSTAGRAM_DM_ENABLED", "true").lower() == "true"
YOUTUBE_ENABLED = os.getenv("YOUTUBE_ENABLED", "false").lower() == "true"
TIKTOK_ENABLED = os.getenv("TIKTOK_ENABLED", "false").lower() == "true"
DM_AUTO_SEND = os.getenv("DM_AUTO_SEND", "false").lower() == "true"
COMMENT_AUTO_REPLY = os.getenv("COMMENT_AUTO_REPLY", "false").lower() == "true"


def platform_enabled(platform: str) -> bool:
    normalized = (platform or "").lower()
    mapping = {
        "facebook_messenger": FACEBOOK_MESSENGER_ENABLED,
        "instagram_dm": INSTAGRAM_DM_ENABLED,
        "youtube": YOUTUBE_ENABLED,
        "tiktok": TIKTOK_ENABLED,
    }
    return mapping.get(normalized, False)


def classify_intent(text: str) -> str:
    lowered = (text or "").lower()
    if "grant" in lowered:
        return "grants"
    if "trade" in lowered:
        return "trading"
    if "set up" in lowered or "llc" in lowered or "ein" in lowered:
        return "business_setup"
    if "credit" in lowered:
        return "credit_help"
    if "fund" in lowered:
        return "funding"
    return "general_interest"


def log_message_event(platform: str, event_type: str, direction: str, payload: dict, status: str = "logged") -> dict:
    return safe_insert("message_logs", {
        "platform": platform,
        "direction": direction,
        "event_type": event_type,
        "external_ref": payload.get("external_ref"),
        "content_topic": payload.get("content_topic"),
        "intent_category": payload.get("intent_category"),
        "payload": payload,
        "status": status,
    })


def route_inbound(platform: str, text: str, source_ref: str = "", content_topic: str = "") -> dict:
    if not platform_enabled(platform):
        return {"ok": False, "error": f"platform_disabled:{platform}"}
    intent = classify_intent(text)
    base_payload = {
        "external_ref": source_ref,
        "content_topic": content_topic,
        "intent_category": intent,
        "text": text,
    }
    log_message_event(platform, "message_received", "inbound", base_payload)
    if platform in {"youtube", "tiktok"}:
        draft = generate_comment_reply(text, platform, content_topic or intent)
        result = safe_insert("social_comments", {
            "platform": platform,
            "external_ref": source_ref,
            "author_handle": "unknown",
            "content_topic": content_topic or intent,
            "comment_text": text,
            "reply_draft": draft["reply"],
            "status": "draft_pending_approval",
            "payload": {"intent_category": intent},
        })
        log_message_event(platform, "message_drafted", "outbound", {**base_payload, "draft": draft["reply"]}, "draft_pending_approval")
        return {"ok": result.get("ok", False), "channel": "comment", "intent": intent, "draft": draft}
    draft = build_dm_draft(handle=source_ref or "lead", platform=platform, intent_category=intent, content_topic=content_topic or intent)
    saved = save_dm_draft(handle=source_ref or "lead", platform=platform, intent_category=intent, content_topic=content_topic or intent)
    log_message_event(platform, "message_drafted", "outbound", {**base_payload, "draft": draft["draft_text"]}, "draft_pending_approval")
    return {"ok": saved.get("ok", False), "channel": "dm", "intent": intent, "draft": draft}
