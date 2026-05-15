#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.nexus_youtube_ops import (
    add_idea,
    create_content_calendar,
    generate_description,
    generate_outline,
    generate_shorts,
    generate_upload_metadata,
    ingest_channel_link,
    ingest_playlist_link,
    list_ideas,
    load_channel_config,
    recommend_revenue_tieins,
    status,
)


def _pp(payload):
    print(json.dumps(payload, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Nexus YouTube channel operations CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("show-config")

    p = sub.add_parser("plan-video")
    p.add_argument("--title", required=True)
    p.add_argument("--pillar", required=True)

    p = sub.add_parser("add-idea")
    p.add_argument("--pillar", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--priority", default="medium")
    p.add_argument("--format", default="long")

    p = sub.add_parser("list-ideas")
    p.add_argument("--status", default="")

    p = sub.add_parser("generate-outline")
    p.add_argument("--title", required=True)
    p.add_argument("--pillar", required=True)

    p = sub.add_parser("generate-description")
    p.add_argument("--title", required=True)
    p.add_argument("--pillar", required=True)

    p = sub.add_parser("generate-shorts")
    p.add_argument("--title", required=True)

    p = sub.add_parser("generate-upload-metadata")
    p.add_argument("--title", required=True)
    p.add_argument("--pillar", required=True)

    p = sub.add_parser("recommend-affiliate-tieins")
    p.add_argument("--pillar", required=True)

    sub.add_parser("create-content-calendar")

    p = sub.add_parser("ingest-channel-link")
    p.add_argument("--url", required=True)

    p = sub.add_parser("ingest-playlist-link")
    p.add_argument("--url", required=True)

    sub.add_parser("status")

    args = parser.parse_args()

    if args.cmd == "show-config":
        _pp(load_channel_config())
        return 0
    if args.cmd == "plan-video":
        _pp({
            "outline": generate_outline(args.title, args.pillar),
            "description": generate_description(args.title, args.pillar),
            "metadata": generate_upload_metadata(args.title, args.pillar),
        })
        return 0
    if args.cmd == "add-idea":
        _pp(add_idea(args.pillar, args.title, priority=args.priority, fmt=args.format))
        return 0
    if args.cmd == "list-ideas":
        _pp(list_ideas(status=args.status or None))
        return 0
    if args.cmd == "generate-outline":
        _pp(generate_outline(args.title, args.pillar))
        return 0
    if args.cmd == "generate-description":
        print(generate_description(args.title, args.pillar))
        return 0
    if args.cmd == "generate-shorts":
        _pp(generate_shorts(args.title))
        return 0
    if args.cmd == "generate-upload-metadata":
        _pp(generate_upload_metadata(args.title, args.pillar))
        return 0
    if args.cmd == "recommend-affiliate-tieins":
        _pp(recommend_revenue_tieins(args.pillar))
        return 0
    if args.cmd == "create-content-calendar":
        _pp(create_content_calendar())
        return 0
    if args.cmd == "ingest-channel-link":
        _pp(ingest_channel_link(args.url))
        return 0
    if args.cmd == "ingest-playlist-link":
        _pp(ingest_playlist_link(args.url))
        return 0
    if args.cmd == "status":
        _pp(status())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
