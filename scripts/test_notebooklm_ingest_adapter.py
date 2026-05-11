#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.notebooklm_ingest_adapter import build_proposed_record, summarize_intake_queue


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    rec = build_proposed_record({
        "notebook_name": "Funding Notebook",
        "topic": "capital ladder",
        "summary": "Map next funding steps.",
        "key_takeaways": ["Need EIN", "Need bank statements"],
        "action_items": ["Collect docs"],
        "category": "funding",
        "confidence": 0.82,
    })
    ok &= check("record source_type", rec.get("source_type") == "notebooklm")
    ok &= check("record dry_run true", rec.get("dry_run") is True)
    text = summarize_intake_queue([rec])
    ok &= check("queue summary includes count", "1 item" in text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
