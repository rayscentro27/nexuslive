#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.knowledge_review_queue import add_proposed_record, list_records, update_status


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    rec = add_proposed_record({"topic": "test", "summary": "queue test"}, source="test")
    ok &= check("record added", bool(rec.get("id")))
    rows = list_records("proposed")
    ok &= check("proposed list returns rows", len(rows) >= 1)
    upd = update_status(rec.get("id"), "reviewed", reviewed_by="tester", notes="ok")
    ok &= check("status update works", bool(upd and upd.get("status") == "reviewed"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
