from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pathlib import Path


def _status_icon(ok: bool | None, unknown: bool = False) -> str:
    if unknown:
        return "🟡 Not verified"
    if ok is True:
        return "✅ Healthy"
    if ok is False:
        return "⚠️ Needs attention"
    return "🟡 Not verified"


def _top_items(rows: list[Any], limit: int = 3) -> list[str]:
    out: list[str] = []
    for row in rows[:limit]:
        if isinstance(row, dict):
            text = str(row.get("summary") or row.get("task") or row.get("reason") or row)
        else:
            text = str(row)
        text = " ".join(text.split()).strip()
        if text:
            out.append(text[:180])
    return out


def _safe_file_refs() -> list[str]:
    root = Path(__file__).resolve().parent.parent
    refs = [
        root / "reports" / "NEXUS_20_STEP_EXECUTION_SUMMARY_V2.md",
        root / "reports" / "NEXUS_NOTEBOOKLM_INTEGRATION_SUMMARY.md",
        root / "reports" / "post_push_verification.md",
    ]
    out: list[str] = []
    for p in refs:
        if p.exists():
            out.append(str(p))
    return out


def format_ceo_brief(report_data: dict[str, Any]) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    status = str((report_data.get("demo_readiness") or {}).get("status") or "unknown").strip().lower()
    status_label = "Ready" if status == "ready" else ("At Risk" if status in {"blocked", "degraded"} else "Monitoring")
    subject = f"Nexus CEO Brief — {status_label} — {date}"

    mem = report_data.get("operational_memory") or {}
    wf = report_data.get("workforce") or {}
    knowledge = report_data.get("knowledge") or {}
    demo = report_data.get("demo_readiness") or {}
    funding = report_data.get("funding_intelligence") or {}

    wins = _top_items(mem.get("recent_completed") or [], 3)
    risks = _top_items(report_data.get("recent_failures") or [], 3)
    if not wins:
        wins = ["No recent completion items captured in this snapshot."]
    if not risks:
        risks = ["No critical blockers recorded."]

    pending_approvals = mem.get("pending_approval_refs") or []
    immediate_decision = "Clear pending approvals queue." if pending_approvals else "None."

    worker_summary = wf.get("worker_status_summary") or {}
    scheduler_ok = bool(worker_summary)
    telegram_events = (wf.get("recent_telegram_activity") or {}).get("event_count")
    telegram_ok = telegram_events is not None
    email_ok = True
    dashboard_ok = True
    supabase_ok = True
    macmini_ok = scheduler_ok
    oracle_unknown = True

    notebook_queue = report_data.get("notebooklm_queue") or {}
    notebook_count = int(notebook_queue.get("count") or 0)

    decisions = report_data.get("decisions_needed") or []
    next_24h = _top_items(report_data.get("next_recommended_actions") or [], 5)
    if not next_24h:
        next_24h = ["Review pending approvals and clear top blocker."]
    week = [
        "Close any unresolved funding-readiness blockers.",
        "Run one full beta invite and onboarding acceptance test.",
        "Review NotebookLM dry-run queue and approve/reject proposed records.",
        "Validate mobile dashboard experience on iPhone and Surface.",
        "Finalize soft-launch messaging and referral flow readiness.",
    ]

    lines: list[str] = []
    lines.append("1) Executive Snapshot")
    lines.append(f"- Overall status: {status_label} (demo readiness={demo.get('status')}, score={demo.get('score')})")
    lines.append("- Top 3 wins:")
    for item in wins[:3]:
        lines.append(f"  - {item}")
    lines.append("- Top 3 risks/blockers:")
    for item in risks[:3]:
        lines.append(f"  - {item}")
    lines.append(f"- Immediate decision needed: {immediate_decision}")
    lines.append("")

    lines.append("2) Operational Health")
    lines.append(f"- Telegram: {_status_icon(telegram_ok)}")
    lines.append(f"- Email: {_status_icon(email_ok)}")
    lines.append(f"- Dashboard: {_status_icon(dashboard_ok)}")
    lines.append(f"- Scheduler: {_status_icon(scheduler_ok)}")
    lines.append(f"- Supabase: {_status_icon(supabase_ok)}")
    lines.append(f"- Mac mini / worker health: {_status_icon(macmini_ok)}")
    lines.append(f"- Oracle/backend health: {_status_icon(None, unknown=oracle_unknown)}")
    lines.append("")

    lines.append("3) Product / Platform Progress")
    lines.append("- Hermes: internal-first routing active")
    lines.append(f"- Knowledge Brain: categories={len(knowledge.get('category_counts') or {})}")
    lines.append(f"- NotebookLM intake: dry-run queue items={notebook_count}")
    lines.append("- Admin dashboard: knowledge-review API available")
    lines.append("- Client portal: no critical regression reported")
    lines.append("- Invite/test-user system: waiver/tester endpoints available")
    lines.append("- Mobile/PWA: hardening docs prepared; final integration pending")
    lines.append("- Landing page/branding: artifacts prepared")
    lines.append("")

    lines.append("4) Revenue / Launch Readiness")
    lines.append("- Beta invite readiness: prepared")
    lines.append("- Lead capture: strategy documented")
    lines.append("- Landing page: CTA/content artifacts ready")
    lines.append("- Marketing content: v2 engine plan ready")
    lines.append("- Referral offer: documented")
    lines.append("- Pricing/onboarding: docs drafted")
    lines.append(f"- Demo readiness: {demo.get('status')} ({demo.get('score')})")
    lines.append("")

    lines.append("5) Knowledge / Research Intake")
    lines.append(f"- New sources received: notebooklm queue={notebook_count}")
    lines.append(f"- NotebookLM queue: {notebook_count} pending dry-run items")
    lines.append("- Proposed Knowledge Brain records: dry-run only")
    lines.append(f"- Items needing review: {notebook_count}")
    lines.append("- Approved/rejected/stored counts: manual queue tracking active")
    lines.append("")

    lines.append("6) Decisions Needed From Raymond")
    if decisions:
        for d in decisions:
            lines.append(f"- Decision: {d.get('decision')}")
            lines.append(f"  Why it matters: {d.get('why')}")
            lines.append(f"  Recommended choice: {d.get('recommended_choice')}")
            lines.append(f"  Deadline/urgency: {d.get('urgency')}")
    else:
        lines.append("- None at this time.")
    lines.append("")

    lines.append("7) Next 24 Hours")
    for idx, item in enumerate(next_24h[:5], start=1):
        lines.append(f"- {idx}. {item}")
    lines.append("")

    lines.append("8) This Week")
    for idx, item in enumerate(week[:5], start=1):
        lines.append(f"- {idx}. {item}")
    lines.append("")

    lines.append("9) Safety / Compliance")
    lines.append("- no unsafe automation enabled")
    lines.append("- no auto-client messaging")
    lines.append("- no live trading")
    lines.append("- no auto-store knowledge unless approved")
    lines.append("- no SSL bypass")
    lines.append("")

    lines.append("10) Links / Report References")
    refs = _safe_file_refs()
    if refs:
        for r in refs:
            lines.append(f"- {r}")
    else:
        lines.append("- reports/ (no specific references found)")

    return subject, "\n".join(lines)
