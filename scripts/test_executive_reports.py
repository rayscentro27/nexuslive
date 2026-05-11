#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.executive_reports import (
    build_executive_report,
    build_weekly_ceo_report,
    build_ai_workforce_summary,
    build_knowledge_brain_report,
    send_executive_report_email,
)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    os.environ["EXECUTIVE_REPORTS_ENABLED"] = "true"

    daily = build_executive_report()
    ok &= check("daily report has sections", isinstance(daily.get("operational_memory"), dict) and isinstance(daily.get("knowledge"), dict))
    ok &= check("daily report includes next actions", isinstance(daily.get("next_recommended_actions"), list) and len(daily.get("next_recommended_actions") or []) >= 1)
    ok &= check("daily report includes telegram activity", isinstance(daily.get("telegram_activity"), dict))

    weekly = build_weekly_ceo_report()
    ok &= check("weekly report includes knowledge context", isinstance((weekly.get("knowledge") or {}).get("category_counts"), dict))

    workforce = build_ai_workforce_summary()
    ok &= check("workforce summary shape", isinstance(workforce.get("latest_agent_runs"), dict))

    kreport = build_knowledge_brain_report()
    ok &= check("knowledge report shape", isinstance(kreport.get("category_counts"), dict))

    def _ok_email(subject: str, body: str):
        return {"sent": True, "configured": True, "error": "", "provider": "smtp_gmail", "recipient_masked": "go***@gmail.com"}

    sent = send_executive_report_email(_ok_email, report_type="daily")
    ok &= check("email success logged honestly", bool((sent.get("email") or {}).get("sent")))

    def _fail_email(subject: str, body: str):
        return {"sent": False, "configured": False, "error": "email notifications not configured", "provider": "smtp_gmail", "recipient_masked": "not-set"}

    failed = send_executive_report_email(_fail_email, report_type="weekly")
    ok &= check("email failure does not claim sent", (failed.get("email") or {}).get("sent") is False)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
