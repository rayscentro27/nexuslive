from __future__ import annotations

import os

from lib.comment_responder import generate_comment_reply
from lib.growth_support import safe_insert

YOUTUBE_ENABLED = os.getenv("YOUTUBE_ENABLED", "false").lower() == "true"
YOUTUBE_COMMENT_REPLY_ENABLED = os.getenv("YOUTUBE_COMMENT_REPLY_ENABLED", "false").lower() == "true"


def fetch_comments(video_id: str, limit: int = 5) -> dict:
    comments = [
        {
            "external_ref": f"yt-{video_id}-{idx}",
            "author_handle": f"viewer_{idx}",
            "comment_text": f"How do I fix my setup before funding? sample {idx}",
            "video_id": video_id,
        }
        for idx in range(1, limit + 1)
    ]
    return {
        "enabled": YOUTUBE_ENABLED,
        "mode": "placeholder",
        "video_id": video_id,
        "comments": comments,
    }


def store_comment(comment: dict, content_topic: str = "youtube_comment") -> dict:
    reply = generate_comment_reply(comment.get("comment_text", ""), "youtube", content_topic)
    return safe_insert("social_comments", {
        "platform": "youtube",
        "external_ref": comment.get("external_ref"),
        "author_handle": comment.get("author_handle"),
        "content_topic": content_topic,
        "comment_text": comment.get("comment_text", ""),
        "reply_draft": reply["reply"],
        "status": "draft_pending_approval",
        "payload": {
            "video_id": comment.get("video_id"),
            "reply_enabled": YOUTUBE_COMMENT_REPLY_ENABLED,
            "placeholder": True,
        },
    })
