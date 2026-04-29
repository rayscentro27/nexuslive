"""
hermes_readiness_brief.py — Hermes daily brief section for client readiness.

Includes missing tasks, next best actions, and readiness score summary.
"""
from __future__ import annotations

from typing import Any

from readiness_engine.guidance_generator import SAFETY_DISCLAIMER


def build_readiness_brief_section(snapshot: dict[str, Any]) -> dict[str, Any]:
    score = snapshot.get("overall_score", 0)
    next_action = snapshot.get("next_best_action")
    tasks = snapshot.get("tasks") or []
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
    completion = snapshot.get("completion") or {}
    overall_pct = completion.get("overall_pct", 0.0)

    high_priority = [t for t in pending_tasks if t.get("priority") == "high"]
    medium_priority = [t for t in pending_tasks if t.get("priority") == "medium"]

    lines = ["── Client Readiness Summary ──"]
    lines.append(f"Overall Readiness Score: {score}/100 (internal estimate only)")
    lines.append(f"Profile Completion: {round(overall_pct * 100, 1)}%")
    lines.append("")

    if next_action:
        lines.append("Next Best Action:")
        lines.append(f"  [{next_action.get('priority','?').upper()}] {next_action.get('task_title','')}")
        lines.append(f"  {next_action.get('task_description','')}")
        lines.append("")

    if high_priority:
        lines.append(f"High Priority Tasks ({len(high_priority)}):")
        for task in high_priority[:3]:
            lines.append(f"  - {task.get('task_title','')}")
        if len(high_priority) > 3:
            lines.append(f"  ... and {len(high_priority) - 3} more")
        lines.append("")

    if medium_priority:
        lines.append(f"Medium Priority Tasks ({len(medium_priority)}):")
        for task in medium_priority[:2]:
            lines.append(f"  - {task.get('task_title','')}")
        lines.append("")

    if not pending_tasks:
        lines.append("All readiness tasks are complete. Well done.")
        lines.append("")

    grant_ready = snapshot.get("grant_ready", False)
    trading_eligible = snapshot.get("trading_eligible", False)
    lines.append(f"Grant Matching Ready: {'Yes' if grant_ready else 'No — complete grant eligibility profile'}")
    lines.append(f"Trading Access: {'Eligible' if trading_eligible else 'Locked — complete education, disclaimer, and paper trading'}")
    lines.append("")
    lines.append(SAFETY_DISCLAIMER)

    brief_text = "\n".join(lines)

    return {
        "brief_text": brief_text,
        "overall_score": score,
        "completion_pct": overall_pct,
        "pending_task_count": len(pending_tasks),
        "next_best_action": next_action,
        "grant_ready": grant_ready,
        "trading_eligible": trading_eligible,
        "disclaimer": SAFETY_DISCLAIMER,
    }


def build_hermes_readiness_brief(
    user_id: str,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    try:
        from readiness_engine.service import build_readiness_snapshot
        snapshot = build_readiness_snapshot(user_id, tenant_id)
    except Exception as exc:
        return {
            "brief_text": f"Readiness data unavailable: {exc}",
            "error": str(exc),
            "disclaimer": SAFETY_DISCLAIMER,
        }
    return build_readiness_brief_section(snapshot)
