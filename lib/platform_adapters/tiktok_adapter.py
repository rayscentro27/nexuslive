from __future__ import annotations

import os

from lib.comment_responder import generate_comment_reply
from lib.growth_support import safe_insert

TIKTOK_ENABLED = os.getenv("TIKTOK_ENABLED", "false").lower() == "true"
TIKTOK_AUTO_POST = os.getenv("TIKTOK_AUTO_POST", "false").lower() == "true"
TIKTOK_COMMENT_REPLY = os.getenv("TIKTOK_COMMENT_REPLY", "false").lower() == "true"


def prepare_post(payload: dict) -> dict:
    return {
        "platform": "tiktok",
        "mode": "manual",
        "ready": True,
        "would_post": False,
        "status": "ready_to_post_manually",
        "payload": payload,
        "enabled": TIKTOK_ENABLED,
        "auto_post_enabled": TIKTOK_AUTO_POST,
    }


def ingest_comment(comment_text: str, content_topic: str, external_ref: str = "tiktok-sim-1", author_handle: str = "viewer") -> dict:
    reply = generate_comment_reply(comment_text, "tiktok", content_topic)
    return safe_insert("social_comments", {
        "platform": "tiktok",
        "external_ref": external_ref,
        "author_handle": author_handle,
        "content_topic": content_topic,
        "comment_text": comment_text,
        "reply_draft": reply["reply"],
        "status": "draft_pending_approval",
        "payload": {
            "reply_enabled": TIKTOK_COMMENT_REPLY,
            "placeholder": True,
        },
    })


def track_engagement(external_ref: str, metrics: dict) -> dict:
    return {
        "platform": "tiktok",
        "external_ref": external_ref,
        "metrics": metrics,
        "mode": "simulated",
        "enabled": TIKTOK_ENABLED,
    }
