from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(score: int) -> int:
    return max(0, min(100, int(score)))


def calculate_operational_health_score(worker_summary: dict[str, Any], task_summary: dict[str, Any], pending_approvals: int) -> dict[str, Any]:
    failed = int(task_summary.get("failed", 0))
    running = int(task_summary.get("running", 0))
    queued = int(task_summary.get("queued", 0))
    offline = int((worker_summary or {}).get("offline", 0))
    score = 100 - (failed * 12) - (pending_approvals * 4) - (offline * 6) - max(0, queued - running)
    reason = "Stable operations" if score >= 75 else "Failures/approvals are reducing operational throughput"
    next_action = "Review pending approvals and failed tasks"
    return {"score": _clamp(score), "reason": reason, "recommended_next_action": next_action, "blocking_issue": "pending_approvals" if pending_approvals else ""}


def calculate_knowledge_freshness_score(knowledge_snapshot: dict[str, Any]) -> dict[str, Any]:
    stale = len(knowledge_snapshot.get("stale_warnings") or [])
    coverage = len([c for c, v in (knowledge_snapshot.get("category_counts") or {}).items() if int(v or 0) > 0])
    score = 100 - stale * 5 + coverage * 2
    reason = "Knowledge coverage and freshness look healthy" if stale < 5 else "Stale knowledge requires refresh"
    return {"score": _clamp(score), "reason": reason, "recommended_next_action": "Refresh stale categories and run ingestion checks", "blocking_issue": "stale_knowledge" if stale >= 10 else ""}


def calculate_agent_readiness_score(agent_activation: dict[str, Any], latest_agent_runs: dict[str, Any]) -> dict[str, Any]:
    enabled = len([v for v in (agent_activation or {}).values() if str(v) != "disabled"])
    failures = 0
    for run in (latest_agent_runs or {}).values():
        email = (run or {}).get("email") or {}
        if email and email.get("sent") is False and email.get("error"):
            failures += 1
    score = 40 + enabled * 10 - failures * 8
    reason = "Controlled agents are available in safe modes" if enabled >= 3 else "Limited safe agent availability"
    return {"score": _clamp(score), "reason": reason, "recommended_next_action": "Enable required review-only/test-only agents", "blocking_issue": "agent_failures" if failures else ""}


def calculate_risk_blocker_score(task_summary: dict[str, Any], pending_approvals: int, stale_workers: int, email_failures: int) -> dict[str, Any]:
    failed = int(task_summary.get("failed", 0))
    score = 100 - failed * 10 - pending_approvals * 8 - stale_workers * 6 - email_failures * 5
    reason = "Risk posture acceptable" if score >= 70 else "Active blockers require attention"
    blocking = []
    if pending_approvals:
        blocking.append("pending_approvals")
    if failed:
        blocking.append("failed_tasks")
    if stale_workers:
        blocking.append("stale_workers")
    if email_failures:
        blocking.append("email_failures")
    return {"score": _clamp(score), "reason": reason, "recommended_next_action": "Clear blockers before scaling execution", "blocking_issue": ",".join(blocking)}


def build_ai_ops_scorecard(*, worker_summary: dict[str, Any], task_summary: dict[str, Any], pending_approvals: int, knowledge_snapshot: dict[str, Any], agent_activation: dict[str, Any], latest_agent_runs: dict[str, Any], stale_workers: int = 0, email_failures: int = 0) -> dict[str, Any]:
    operational = calculate_operational_health_score(worker_summary, task_summary, pending_approvals)
    knowledge = calculate_knowledge_freshness_score(knowledge_snapshot)
    readiness = calculate_agent_readiness_score(agent_activation, latest_agent_runs)
    funding_credit_available = int(bool((knowledge_snapshot.get("recent_funding_insights") or []))) + int(bool((knowledge_snapshot.get("recent_credit_insights") or [])))
    funding_credit = {
        "score": _clamp(40 + funding_credit_available * 30),
        "reason": "Funding/credit intelligence available" if funding_credit_available else "Limited funding/credit insight coverage",
        "recommended_next_action": "Refresh funding and credit ingestion sources",
        "blocking_issue": "missing_funding_credit_context" if funding_credit_available == 0 else "",
    }
    risk = calculate_risk_blocker_score(task_summary, pending_approvals, stale_workers, email_failures)
    return {
        "generated_at": _now(),
        "operational_health": operational,
        "knowledge_freshness": knowledge,
        "agent_readiness": readiness,
        "funding_credit_intelligence": funding_credit,
        "risk_blocker": risk,
        "read_only": True,
    }
