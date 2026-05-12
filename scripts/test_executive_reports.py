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
import lib.executive_reports as er


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    os.environ["EXECUTIVE_REPORTS_ENABLED"] = "true"

    orig_knowledge = er.build_knowledge_brain_report
    orig_workforce = er.build_ai_workforce_summary
    orig_collab = er.dry_run_collaboration_plan
    orig_ops = er.build_operational_intelligence_snapshot
    orig_funding = er.build_client_funding_intelligence_summary
    orig_trading = er.build_trading_intelligence_report
    orig_opp = er.build_opportunity_intelligence_summary
    orig_exec = er.build_executive_strategy_summary
    er.build_knowledge_brain_report = lambda: {"category_counts": {}, "stale_warnings": [], "recent_funding_insights": [], "recent_credit_insights": []}
    er.build_ai_workforce_summary = lambda: {"latest_agent_runs": {}, "recent_failures": [], "recent_telegram_activity": {}, "worker_status_summary": {}, "job_queue_status_summary": {}}
    er.dry_run_collaboration_plan = lambda prompt: {"can_execute": False, "execution_mode": "preview_only"}
    er.build_operational_intelligence_snapshot = lambda mode="detailed": {"executive_summary": "ok", "risk_level": "low"}
    er.build_client_funding_intelligence_summary = lambda: {"enabled": True, "next_best_funding_action": "collect docs"}
    er.build_trading_intelligence_report = lambda: {"enabled": True, "trading_paper_only": True}
    er.build_opportunity_intelligence_summary = lambda: {"enabled": True, "opportunity_next_action": "review opportunities"}
    er.build_executive_strategy_summary = lambda: {"next_domain_focus": {"domain": "operations"}}

    def _ok_email(subject: str, body: str):
        return {"sent": True, "configured": True, "error": "", "provider": "smtp_gmail", "recipient_masked": "go***@gmail.com"}

    def _fail_email(subject: str, body: str):
        return {"sent": False, "configured": False, "error": "email notifications not configured", "provider": "smtp_gmail", "recipient_masked": "not-set"}

    try:
        daily = build_executive_report()
        ok &= check("daily report has sections", isinstance(daily.get("operational_memory"), dict) and isinstance(daily.get("knowledge"), dict))
        ok &= check("daily report includes next actions", isinstance(daily.get("next_recommended_actions"), list) and len(daily.get("next_recommended_actions") or []) >= 1)
        ok &= check("daily report includes telegram activity", isinstance(daily.get("telegram_activity"), dict))
        ok &= check("daily report includes delta summary", isinstance(daily.get("delta_summary"), dict) and isinstance((daily.get("delta_summary") or {}).get("recommended_focus_areas"), list))

        weekly = build_weekly_ceo_report()
        ok &= check("weekly report includes knowledge context", isinstance((weekly.get("knowledge") or {}).get("category_counts"), dict))

        workforce = build_ai_workforce_summary()
        ok &= check("workforce summary shape", isinstance(workforce.get("latest_agent_runs"), dict))

        kreport = build_knowledge_brain_report()
        ok &= check("knowledge report shape", isinstance(kreport.get("category_counts"), dict))

        sent = send_executive_report_email(_ok_email, report_type="daily")
        ok &= check("email success logged honestly", bool((sent.get("email") or {}).get("sent")))

        failed = send_executive_report_email(_fail_email, report_type="weekly")
        ok &= check("email failure does not claim sent", (failed.get("email") or {}).get("sent") is False)
    finally:
        er.build_knowledge_brain_report = orig_knowledge
        er.build_ai_workforce_summary = orig_workforce
        er.dry_run_collaboration_plan = orig_collab
        er.build_operational_intelligence_snapshot = orig_ops
        er.build_client_funding_intelligence_summary = orig_funding
        er.build_trading_intelligence_report = orig_trading
        er.build_opportunity_intelligence_summary = orig_opp
        er.build_executive_strategy_summary = orig_exec

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
