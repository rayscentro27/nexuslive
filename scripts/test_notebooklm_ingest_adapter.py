#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib import notebooklm_ingest_adapter as adapter


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    rec = adapter.build_proposed_record({
        "notebook_name": "Nexus Funding",
        "domain": "funding",
        "summary": "Map next funding steps. Build risk-aware sequence.",
        "source_urls": ["https://example.com/funding"],
        "insights": ["Need EIN", "Need bank statements"],
        "source_count": 2,
        "dry_run": True,
    })
    ok &= check("record source_type", rec.get("source_type") == "notebooklm")
    ok &= check("record proposed status", rec.get("status") == "proposed")
    ok &= check("record dry_run true", rec.get("dry_run") is True)
    ok &= check("record has dedup key", bool((rec.get("metadata") or {}).get("dedup_key")))
    text = adapter.summarize_intake_queue([rec])
    ok &= check("queue summary includes count", "1 item" in text)

    ok &= check(
        "notebook config mapping",
        adapter.NOTEBOOK_DOMAIN_MAP.get("Nexus Grants") == "grants" and adapter.NOTEBOOK_DOMAIN_MAP.get("Nexus Trading") == "trading",
    )

    original_fetch = adapter.fetch_named_notebook_payload
    original_get = adapter._existing_dedup_keys
    original_post = adapter._supabase_post
    try:
        adapter.fetch_named_notebook_payload = lambda name: {
            "ok": True,
            "notebook_name": name,
            "summary": "Digest line one\nDigest line two",
            "sources": [{"url": "https://youtube.com/watch?v=abc12345678"}],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
        }
        dry = adapter.ingest_named_notebook("Nexus Grants", apply=False)
        ok &= check("dry-run ingest ok", dry.get("ok") is True and dry.get("apply") is False)
        ok &= check("dry-run proposed domain mapping", (dry.get("proposed_record") or {}).get("domain") == "grants")

        adapter._existing_dedup_keys = lambda: {((dry.get("proposed_record") or {}).get("metadata") or {}).get("dedup_key")}
        adapter._supabase_post = lambda path, payload: payload
        apply_dup = adapter.ingest_named_notebook("Nexus Grants", apply=True)
        ok &= check("duplicate prevention", int(apply_dup.get("duplicates") or 0) >= 1)
    finally:
        adapter.fetch_named_notebook_payload = original_fetch
        adapter._existing_dedup_keys = original_get
        adapter._supabase_post = original_post

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
