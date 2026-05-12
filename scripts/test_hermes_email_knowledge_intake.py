#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.hermes_email_knowledge_intake import parse_knowledge_email, ingest_knowledge_email_dry_run


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    subject = "Knowledge Load - Funding Research"
    body = """
    Priority: high
    Tags: funding, credit
    Links:
    https://example.com/business-funding-guide
    https://youtube.com/watch?v=abcd1234
    """
    parsed = parse_knowledge_email("ray@example.com", subject, body, message_id="msg-1")
    ok &= check("url extraction", len(parsed.urls) == 2)
    ok &= check("youtube detection", len(parsed.youtube_links) == 1)
    ok &= check("category detection", parsed.requested_category == "funding")
    ok &= check("priority detection", parsed.priority == "high")

    one = ingest_knowledge_email_dry_run("ray@example.com", subject, body, message_id="msg-dup")
    two = ingest_knowledge_email_dry_run("ray@example.com", subject, body, message_id="msg-dup")
    ok &= check("dry-run report generated", bool(one.get("report_path")))
    ok &= check("dry-run does not require write enable", bool(one.get("dry_run")) is True)
    ok &= check("duplicate detection increments", int(two.get("duplicates") or 0) >= 1)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
