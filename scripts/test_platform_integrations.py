#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.message_router import route_inbound
from lib.platform_adapters.tiktok_adapter import ingest_comment as ingest_tiktok_comment, prepare_post
from lib.platform_adapters.youtube_adapter import fetch_comments, store_comment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    youtube_sample = fetch_comments("sample-video", limit=2)
    youtube_store = store_comment(youtube_sample["comments"][0], content_topic="business funding")
    tiktok_store = ingest_tiktok_comment("How do I get business funding?", "business funding", external_ref="tik-1", author_handle="viewer_1")
    dm_route = route_inbound("instagram_dm", "How do I get business funding?", source_ref="ig-user-1", content_topic="business funding")
    comment_route = route_inbound("youtube", "How do I fix my business setup?", source_ref="yt-comment-1", content_topic="business setup")

    report = {
        "dry_run": args.dry_run,
        "platforms_detected": {
            "facebook_messenger_enabled": os.getenv("FACEBOOK_MESSENGER_ENABLED", "true"),
            "instagram_dm_enabled": os.getenv("INSTAGRAM_DM_ENABLED", "true"),
            "youtube_enabled": os.getenv("YOUTUBE_ENABLED", "false"),
            "tiktok_enabled": os.getenv("TIKTOK_ENABLED", "false"),
        },
        "live_vs_placeholder": {
            "facebook_messenger": "existing integration assumed live; no logic changed",
            "instagram_dm": "existing integration assumed live; no logic changed",
            "youtube": "placeholder draft-only adapter",
            "tiktok": "placeholder draft-only adapter",
        },
        "youtube_sample": youtube_sample,
        "youtube_store": youtube_store,
        "tiktok_prepare_post": prepare_post({"caption": "draft", "asset_ref": "content-1"}),
        "tiktok_store": tiktok_store,
        "instagram_dm_route": dm_route,
        "youtube_comment_route": comment_route,
        "messages_sent": 0,
        "comments_replied_live": 0,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
