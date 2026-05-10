#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.ceo_report_formatter import format_ceo_brief


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    payload = {
        "demo_readiness": {"status": "ready", "score": 100},
        "operational_memory": {"recent_completed": [{"task": "SSL repaired"}], "pending_approval_refs": []},
        "recent_failures": [],
        "workforce": {"worker_status_summary": {"running": 3}, "recent_telegram_activity": {"event_count": 5}},
        "knowledge": {"category_counts": {"funding": 4}},
        "next_recommended_actions": ["Clear blockers", "Run invite test"],
    }
    subject, body = format_ceo_brief(payload)
    ok &= check("subject format includes CEO brief", subject.startswith("Nexus CEO Brief —"))
    ok &= check("executive snapshot included", "1) Executive Snapshot" in body)
    ok &= check("grouped operational health included", "2) Operational Health" in body)
    ok &= check("safety section always included", "9) Safety / Compliance" in body)
    ok &= check("decisions section present", "6) Decisions Needed From Raymond" in body)
    ok &= check("none decisions line when empty", "None at this time" in body)
    ok &= check("no secret leakage", "NEXUS_EMAIL_PASSWORD" not in body and "OPENROUTER_API_KEY" not in body)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
