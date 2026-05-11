from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Callable

from lib import hermes_ops_memory
from lib.hermes_knowledge_brain import get_top_ranked_knowledge


def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _email(send_report_email: Callable[[str, str], Any] | None, subject: str, body: str) -> dict[str, Any]:
    fallback = {"sent": False, "configured": False, "error": "email_not_attempted", "subject": subject, "provider": "smtp_gmail", "recipient_masked": "not-set"}
    if not send_report_email:
        return fallback
    result = send_report_email(subject, body)
    if isinstance(result, dict):
        out = dict(fallback)
        out.update(result)
        out["subject"] = subject
        return out
    fallback["sent"] = True
    fallback["configured"] = True
    fallback["error"] = ""
    return fallback


def _save_latest(memory: dict[str, Any], role_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    latest = dict(memory.get("latest_agent_runs") or {})
    latest[role_id] = payload
    memory["latest_agent_runs"] = latest
    return hermes_ops_memory.save_memory(memory, updated_by=f"agent_{role_id}")


def _run_qa_test_agent(send_report_email: Callable[[str, str], Any] | None) -> dict[str, Any]:
    if not _flag("QA_TEST_AGENT_ENABLED", "false"):
        return {"ok": False, "message": "QA/Test Agent is disabled.", "can_execute": False}
    cmd = [
        "python3", "scripts/test_telegram_policy.py",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=os.path.dirname(os.path.dirname(__file__)))
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    passed = output.count("PASS")
    failed = output.count("FAIL")
    subject = f"Nexus QA Check - {_now()}"
    email = _email(send_report_email, subject, output[:120000])
    memory = hermes_ops_memory.load_memory(updated_by="qa_test_agent")
    _save_latest(memory, "qa_test", {"timestamp": _now(), "mode": "test-only", "passed": passed, "failed": failed, "email": email, "read_only": True})
    return {"ok": True, "read_only": True, "can_execute": False, "result": {"passed": passed, "failed": failed}, "email": email}


def _run_report_writer_agent(send_report_email: Callable[[str, str], Any] | None) -> dict[str, Any]:
    if not _flag("REPORT_WRITER_AGENT_ENABLED", "false"):
        return {"ok": False, "message": "Report Writer Agent is disabled.", "can_execute": False}
    memory = hermes_ops_memory.load_memory(updated_by="report_writer_agent")
    body = "\n".join([
        "Nexus Executive Summary",
        f"Timestamp: {_now()}",
        f"Active priorities: {memory.get('active_priorities') or []}",
        f"Task lifecycle summary: {memory.get('task_lifecycle_summary') or {}}",
        f"Recent completed: {memory.get('recent_completed') or []}",
        f"Recent failed: {memory.get('recent_failed') or []}",
        f"Pending approvals: {memory.get('pending_approval_refs') or []}",
        f"Latest ops monitor run: {memory.get('latest_ops_monitor_run') or {}}",
    ])
    subject = f"Nexus Executive Report - {_now()}"
    email = _email(send_report_email, subject, body)
    _save_latest(memory, "report_writer", {"timestamp": _now(), "mode": "email-only", "email": email, "read_only": True})
    return {"ok": True, "read_only": True, "can_execute": False, "result": {"summary": "executive report prepared"}, "email": email}


def _run_telegram_comms_agent() -> dict[str, Any]:
    if not _flag("TELEGRAM_COMMS_AGENT_APPROVAL_ONLY", "false"):
        return {"ok": False, "message": "Telegram/Comms Agent is disabled.", "can_execute": False}
    memory = hermes_ops_memory.load_memory(updated_by="telegram_comms_agent")
    draft = {
        "timestamp": _now(),
        "mode": "approval-only",
        "draft": "Quick ops update draft: System is stable, pending approvals are being tracked, and detailed reports are available by email.",
        "approval_required": True,
        "can_send_external": False,
        "read_only": True,
    }
    _save_latest(memory, "telegram_comms", draft)
    return {"ok": True, "read_only": True, "can_execute": False, "result": draft, "email": {"sent": False, "configured": False, "error": "draft_only"}}


def _run_funding_strategy_agent(send_report_email: Callable[[str, str], Any] | None) -> dict[str, Any]:
    if not _flag("FUNDING_STRATEGY_AGENT_REVIEW_ONLY", "false"):
        return {"ok": False, "message": "Funding Strategy Agent is disabled.", "can_execute": False}
    memory = hermes_ops_memory.load_memory(updated_by="funding_strategy_agent")
    recommendations = memory.get("recent_recommendations") or []
    body = "\n".join([
        "Funding Strategy Review (Review-only)",
        f"Timestamp: {_now()}",
        f"Top recommendations: {recommendations[:5]}",
        "Actions blocked: submit applications, billing changes, client messaging.",
    ])
    email = _email(send_report_email, f"Nexus Funding Strategy Review - {_now()}", body)
    _save_latest(memory, "funding_strategy", {"timestamp": _now(), "mode": "review-only", "email": email, "read_only": True})
    return {"ok": True, "read_only": True, "can_execute": False, "result": {"recommendations": recommendations[:5]}, "email": email}


def _run_credit_workflow_agent(send_report_email: Callable[[str, str], Any] | None) -> dict[str, Any]:
    if not _flag("CREDIT_WORKFLOW_AGENT_REVIEW_ONLY", "false"):
        return {"ok": False, "message": "Credit Workflow Agent is disabled.", "can_execute": False}
    memory = hermes_ops_memory.load_memory(updated_by="credit_workflow_agent")
    blocked = memory.get("blocked_priorities") or []
    body = "\n".join([
        "Credit Workflow Review (Review-only)",
        f"Timestamp: {_now()}",
        f"Blocked workflow items: {blocked[:8]}",
        "Actions blocked: dispute submissions, external letters, client messaging.",
    ])
    email = _email(send_report_email, f"Nexus Credit Workflow Review - {_now()}", body)
    _save_latest(memory, "credit_workflow", {"timestamp": _now(), "mode": "review-only", "email": email, "read_only": True})
    return {"ok": True, "read_only": True, "can_execute": False, "result": {"blocked_items": blocked[:8]}, "email": email}


def _run_grants_research_agent(send_report_email: Callable[[str, str], Any] | None) -> dict[str, Any]:
    if not _flag("GRANTS_RESEARCH_AGENT_REVIEW_ONLY", "true"):
        return {"ok": False, "message": "Grants Research Agent is disabled.", "can_execute": False}
    rows = get_top_ranked_knowledge("grants", limit=6)
    body = "\n".join([
        "Grants Research Review (review-only)",
        f"Timestamp: {_now()}",
        "Top grants signals:",
        *[f"- {str(r.get('summary') or '')}" for r in rows],
    ])
    email = _email(send_report_email, f"Nexus Grants Research Review - {_now()}", body)
    memory = hermes_ops_memory.load_memory(updated_by="grants_research_agent")
    _save_latest(memory, "grants_research", {"timestamp": _now(), "mode": "review-only", "email": email, "read_only": True})
    return {"ok": True, "read_only": True, "can_execute": False, "result": {"top_grants": rows}, "email": email}


def _run_business_setup_agent(send_report_email: Callable[[str, str], Any] | None) -> dict[str, Any]:
    if not _flag("BUSINESS_SETUP_AGENT_REVIEW_ONLY", "true"):
        return {"ok": False, "message": "Business Setup Agent is disabled.", "can_execute": False}
    rows = get_top_ranked_knowledge("business_setup", limit=6)
    body = "\n".join([
        "Business Setup Review (review-only)",
        f"Timestamp: {_now()}",
        "Top business setup signals:",
        *[f"- {str(r.get('summary') or '')}" for r in rows],
    ])
    email = _email(send_report_email, f"Nexus Business Setup Review - {_now()}", body)
    memory = hermes_ops_memory.load_memory(updated_by="business_setup_agent")
    _save_latest(memory, "business_setup", {"timestamp": _now(), "mode": "review-only", "email": email, "read_only": True})
    return {"ok": True, "read_only": True, "can_execute": False, "result": {"top_business_setup": rows}, "email": email}


def _run_trading_research_agent(send_report_email: Callable[[str, str], Any] | None) -> dict[str, Any]:
    if not _flag("TRADING_RESEARCH_AGENT_RESEARCH_ONLY", "true"):
        return {"ok": False, "message": "Trading Research Agent is disabled.", "can_execute": False}
    rows = get_top_ranked_knowledge("trading", limit=6)
    body = "\n".join([
        "Trading Research Summary (research-only)",
        f"Timestamp: {_now()}",
        "Top trading research signals:",
        *[f"- {str(r.get('summary') or '')}" for r in rows],
        "No trade execution is performed in this mode.",
    ])
    email = _email(send_report_email, f"Nexus Trading Research Summary - {_now()}", body)
    memory = hermes_ops_memory.load_memory(updated_by="trading_research_agent")
    _save_latest(memory, "trading_research", {"timestamp": _now(), "mode": "research-only", "email": email, "read_only": True})
    return {"ok": True, "read_only": True, "can_execute": False, "result": {"top_trading_research": rows}, "email": email}


def run_controlled_agent(role_id: str, send_report_email: Callable[[str, str], Any] | None = None) -> dict[str, Any]:
    dispatch = {
        "qa_test": lambda: _run_qa_test_agent(send_report_email),
        "report_writer": lambda: _run_report_writer_agent(send_report_email),
        "telegram_comms": _run_telegram_comms_agent,
        "funding_strategy": lambda: _run_funding_strategy_agent(send_report_email),
        "credit_workflow": lambda: _run_credit_workflow_agent(send_report_email),
        "grants_research": lambda: _run_grants_research_agent(send_report_email),
        "business_setup": lambda: _run_business_setup_agent(send_report_email),
        "trading_research": lambda: _run_trading_research_agent(send_report_email),
    }
    fn = dispatch.get(role_id)
    if not fn:
        return {"ok": False, "message": "Unsupported controlled agent.", "can_execute": False}
    result = fn()
    result.setdefault("read_only", True)
    result.setdefault("can_execute", False)
    result.setdefault("dry_run_only", True)
    return result
