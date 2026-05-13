#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import lib.hermes_email_knowledge_intake as intake


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    meta = intake.classify_mobile_subject("trading youtube strategy")
    ok &= check("subject parser trading", meta.get("domain") == "trading" and meta.get("source_type") == "youtube")

    parsed = intake.parse_knowledge_email(
        "Ray <ray@example.com>",
        "trading youtube strategy",
        "Channel:\nhttps://www.youtube.com/@nitrotrades\nReview last 10 videos\nhttps://www.youtube.com/watch?v=abc12345678",
        message_id="<nitro-test-1>",
    )
    ok &= check("nitro email parse", "nitrotrades" in " ".join(parsed.urls).lower())

    orig_channel = intake._youtube_channel_videos
    orig_transcript = intake._youtube_transcript
    try:
        intake._youtube_channel_videos = lambda _u, max_videos=10: [
            "https://www.youtube.com/watch?v=abc12345678",
            "https://www.youtube.com/watch?v=def12345678",
        ][:max_videos]
        intake._youtube_transcript = lambda _u: ("silver bullet setup entry timing risk management", "ok")

        result = intake.ingest_email_to_transcript_queue(parsed, apply=False, max_channel_videos=10)
        ok &= check("youtube expansion", result.get("expanded_urls", 0) >= 2)
        ok &= check("transcript rows prepared", result.get("transcript_rows_prepared", 0) >= 2)
        ok &= check("knowledge rows prepared", result.get("knowledge_rows_prepared", 0) >= 2)
        ok &= check("dry-run no writes", result.get("transcript_rows_inserted", 0) == 0 and result.get("knowledge_rows_inserted", 0) == 0)

        # duplicate prevention check by stubbing existing URL lookup
        def _fake_get(path: str, params: dict[str, str] | None = None):
            if path == "transcript_queue" and params and params.get("source_url", "").endswith("abc12345678"):
                return [{"source_url": "https://www.youtube.com/watch?v=abc12345678"}]
            return []

        orig_get = intake._supabase_get
        intake._supabase_get = _fake_get
        result2 = intake.ingest_email_to_transcript_queue(parsed, apply=True, max_channel_videos=10)
        ok &= check("duplicate prevention path", result2.get("duplicates_skipped", 0) >= 1)
    finally:
        intake._youtube_channel_videos = orig_channel
        intake._youtube_transcript = orig_transcript
        if "orig_get" in locals():
            intake._supabase_get = orig_get

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
