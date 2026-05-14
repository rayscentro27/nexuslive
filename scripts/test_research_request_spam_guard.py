#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import lib.research_request_service as rrs
from lib.ai_employee_knowledge_router import KnowledgeResult


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def main() -> int:
    ok = True

    original_writes = rrs.WRITES_ENABLED
    original_urlopen = rrs.urllib.request.urlopen
    rrs.WRITES_ENABLED = True

    try:
        def fake_urlopen(req, timeout=8):
            url = getattr(req, "full_url", "")
            if "research_requests?" in url and "normalized_query=eq." in url:
                return _Resp([{"id": "dup-1", "status": "researching", "created_at": "2026-05-14T00:00:00Z"}])
            return _Resp([])

        rrs.urllib.request.urlopen = fake_urlopen
        result = KnowledgeResult(status="not_found", confidence=10, sources=[], summary="", escalation_needed=True)
        out = rrs.create_research_ticket(
            role="trading_analyst",
            query="ict silver bullet",
            original_question="ict silver bullet",
            result=result,
            user_id="u-1",
        )
        ok &= check("recent normalized duplicate suppressed", out.get("status") == "duplicate")
        ok &= check("duplicate ticket id returned", out.get("ticket_id") == "dup-1")
    finally:
        rrs.WRITES_ENABLED = original_writes
        rrs.urllib.request.urlopen = original_urlopen

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
