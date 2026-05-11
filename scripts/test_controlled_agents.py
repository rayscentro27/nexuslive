#!/usr/bin/env python3
"""Tests for controlled agent activation and safety constraints."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    os.environ["QA_TEST_AGENT_ENABLED"] = "true"
    os.environ["REPORT_WRITER_AGENT_ENABLED"] = "true"
    os.environ["TELEGRAM_COMMS_AGENT_APPROVAL_ONLY"] = "true"
    os.environ["FUNDING_STRATEGY_AGENT_REVIEW_ONLY"] = "true"
    os.environ["CREDIT_WORKFLOW_AGENT_REVIEW_ONLY"] = "true"
    os.environ["SWARM_EXECUTION_ENABLED"] = "false"
    os.environ["HERMES_SWARM_DRY_RUN"] = "true"
    os.environ["GRANTS_RESEARCH_AGENT_REVIEW_ONLY"] = "true"
    os.environ["BUSINESS_SETUP_AGENT_REVIEW_ONLY"] = "true"
    os.environ["TRADING_RESEARCH_AGENT_RESEARCH_ONLY"] = "true"

    from lib.controlled_agents import run_controlled_agent
    from lib.swarm_coordinator import AGENT_REGISTRY

    def _fake_email(subject: str, body: str):
        return {
            "ok": False,
            "sent": False,
            "configured": False,
            "provider": "smtp_gmail",
            "recipient_masked": "ra***@example.com",
            "error": "email notifications not configured",
        }

    qa = run_controlled_agent("qa_test", send_report_email=_fake_email)
    ok &= check("QA agent runs in test-only mode", qa.get("ok") is True and qa.get("read_only") is True)
    ok &= check("QA agent stays non-executable", qa.get("can_execute") is False and qa.get("dry_run_only") is True)

    writer = run_controlled_agent("report_writer", send_report_email=_fake_email)
    ok &= check("Report Writer runs", writer.get("ok") is True)
    ok &= check("Report Writer email fallback is explicit", (writer.get("email") or {}).get("sent") is False)

    comms = run_controlled_agent("telegram_comms", send_report_email=_fake_email)
    ok &= check("Comms agent is approval-only", (comms.get("result") or {}).get("approval_required") is True)
    ok &= check("Comms agent cannot send external", (comms.get("result") or {}).get("can_send_external") is False)

    funding = run_controlled_agent("funding_strategy", send_report_email=_fake_email)
    ok &= check("Funding agent review-only", funding.get("ok") is True and funding.get("can_execute") is False)

    credit = run_controlled_agent("credit_workflow", send_report_email=_fake_email)
    ok &= check("Credit agent review-only", credit.get("ok") is True and credit.get("can_execute") is False)

    grants = run_controlled_agent("grants_research", send_report_email=_fake_email)
    ok &= check("Grants agent review-only", grants.get("ok") is True and grants.get("can_execute") is False)

    business = run_controlled_agent("business_setup", send_report_email=_fake_email)
    ok &= check("Business setup agent review-only", business.get("ok") is True and business.get("can_execute") is False)

    trading = run_controlled_agent("trading_research", send_report_email=_fake_email)
    ok &= check("Trading research agent research-only", trading.get("ok") is True and trading.get("can_execute") is False)

    ok &= check("No controlled agent can send Telegram directly", all((AGENT_REGISTRY.get(k) or {}).get("telegram_allowed") is False for k in ["ops_monitor", "qa_test", "report_writer", "telegram_comms", "funding_strategy", "credit_workflow"]))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
