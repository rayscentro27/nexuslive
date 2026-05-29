"""
hermes_daily_monetization_digest.py
=======================================
Build the daily Telegram-ready recommendation digest for Ray.

Follows anti-spam policy: one digest per cycle, common language,
no raw logs, evidence paths where useful.

Ray needs to see results clearly so he can trust the system.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = ROOT / "docs" / "reports" / "review"


def build_digest(
    intake_results: dict,
    decision_results: dict,
) -> dict:
    """
    Build the daily digest from intake + decision cycle results.

    Returns:
      telegram_message: str  — concise Telegram-ready text
      review_md_path: str    — path to full human-readable review artifact
      review_json_path: str  — path to JSON review artifact
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    intake_stats  = intake_results.get("stats", {})
    top_ops       = decision_results.get("top_opportunities", [])
    rejected      = decision_results.get("rejected", [])
    needs_approval = decision_results.get("needs_approval", [])
    blockers      = decision_results.get("blockers", [])
    top_rec       = decision_results.get("top_recommendation", "")

    total_sources  = intake_stats.get("total", 0)
    useful_sources = len(top_ops)
    rejected_count = len(rejected)
    fallback_count = intake_stats.get("fallbacks", 0)

    # ── Telegram message (max ~600 chars) ────────────────────────────────────

    lines = [
        "📊 **Hermes Daily Digest**",
        "",
        f"I reviewed {total_sources} sources. {useful_sources} look useful. "
        f"{rejected_count} were rejected.",
    ]

    if fallback_count:
        lines.append(
            f"{fallback_count} sources need manual research (no API available — tasks created)."
        )

    if top_rec:
        lines.append(f"\n**Best move:** {top_rec}")

    # Source breakdown
    yt   = intake_stats.get("youtube", 0)
    goog = intake_stats.get("google", 0)
    gh   = intake_stats.get("github", 0)
    mon  = intake_stats.get("monetization", 0)
    soc  = intake_stats.get("social", 0)
    lines += [
        "",
        "**Sources collected:**",
        f"  • YouTube: {yt}  • Google/web: {goog}  • GitHub: {gh}",
        f"  • Social/trend: {soc}  • Monetization: {mon}",
    ]

    # Top 3 opportunities
    if top_ops:
        lines.append("\n**Top 3 opportunities:**")
        for i, op in enumerate(top_ops[:3], 1):
            title = op.get("title", "")[:60]
            score = op.get("monetization_score", 0)
            status = op.get("status", "")
            lines.append(f"  {i}. {title} [{status}, score {score}]")

    # Needs approval
    if needs_approval:
        lines.append("\n**Needs your approval:**")
        for item in needs_approval[:2]:
            lines.append(f"  ⏳ {item.get('title','')[:50]} — {item.get('approval_reason','')[:50]}")

    # Blockers
    if blockers:
        lines.append("\n**Blockers:**")
        for b in (blockers if isinstance(blockers, list) else [blockers])[:2]:
            lines.append(f"  🔴 {b}")

    # Evidence
    intake_path  = intake_results.get("artifact_path", intake_results.get("md_path", ""))
    decision_path = decision_results.get("md_path", "")
    if intake_path or decision_path:
        lines.append("")
        if intake_path:
            lines.append(f"Intake: `{intake_path}`")
        if decision_path:
            lines.append(f"Decisions: `{decision_path}`")

    lines += [
        "",
        "_Reply: `show top actions` | `show rejected` | `show daily review` | `continue research`_",
    ]

    telegram_message = "\n".join(lines)
    # Trim if needed (Telegram message limit)
    if len(telegram_message) > 4000:
        telegram_message = telegram_message[:3900] + "\n...(truncated)"

    # ── Full review artifact ──────────────────────────────────────────────────

    review_md_path, review_json_path = _write_review_artifact(
        ts=ts,
        intake_results=intake_results,
        decision_results=decision_results,
        telegram_message=telegram_message,
    )

    return {
        "telegram_message": telegram_message,
        "review_md_path": review_md_path,
        "review_json_path": review_json_path,
        "top_opportunities": top_ops,
        "total_sources": total_sources,
        "useful_sources": useful_sources,
        "rejected_count": rejected_count,
    }


def _write_review_artifact(
    ts: str,
    intake_results: dict,
    decision_results: dict,
    telegram_message: str,
) -> tuple[str, str]:
    """Write full human-readable daily research review artifact."""
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    md_path   = REVIEW_DIR / f"daily_research_review_{ts}.md"
    json_path = REVIEW_DIR / f"daily_research_review_{ts}.json"

    intake_stats = intake_results.get("stats", {})
    top_ops      = decision_results.get("top_opportunities", [])
    rejected     = decision_results.get("rejected", [])
    needs_approval = decision_results.get("needs_approval", [])

    # Determine which scouts were dispatched
    scouts_dispatched = list({
        op.get("assigned_scout", "")
        for op in top_ops
        if op.get("assigned_scout")
    })

    md = [
        "# Daily Research Review",
        f"*{ts[:8]} {ts[9:11]}:{ts[11:13]} UTC*",
        "",
        "## What Nexus Searched",
        "",
        "- YouTube: channel registry, keyword searches",
        "- Google/web: keyword research (fallback tasks if API unavailable)",
        "- GitHub: trend research outputs",
        "- Social/trend: structured manual research tasks",
        "- Monetization categories: affiliate, lead magnet, content, product",
        "",
        "## Sources Collected",
        "",
        f"- Total: {intake_stats.get('total', 0)}",
        f"- YouTube: {intake_stats.get('youtube', 0)}",
        f"- Google/web: {intake_stats.get('google', 0)}",
        f"- GitHub: {intake_stats.get('github', 0)}",
        f"- Social/trend: {intake_stats.get('social', 0)}",
        f"- Monetization: {intake_stats.get('monetization', 0)}",
        f"- Fallback tasks (source unavailable): {intake_stats.get('fallbacks', 0)}",
        f"- Real sources with data: {intake_stats.get('real_sources', 0)}",
        "",
        "## What Was Useful",
        "",
    ]

    for i, op in enumerate(top_ops[:10], 1):
        title  = op.get("title", "")[:80]
        score  = op.get("monetization_score", 0)
        status = op.get("status", "")
        why    = op.get("why_selected", "")
        rec    = op.get("recommended_action", "")
        md.append(f"### {i}. {title}")
        md.append(f"- Score: {score} | Status: {status}")
        if why:
            md.append(f"- Why: {why}")
        if rec:
            md.append(f"- Next: {rec}")
        md.append("")

    md += [
        "## What Was Rejected",
        "",
    ]
    if rejected:
        for op in rejected[:10]:
            title  = op.get("title", "")[:70]
            reason = op.get("why_rejected", "Low score")
            score  = op.get("monetization_score", 0)
            md.append(f"- ❌ {title} (score {score}) — {reason}")
    else:
        md.append("- No sources rejected in this cycle.")
    md.append("")

    md += [
        "## What Hermes Recommends",
        "",
    ]
    top_rec = decision_results.get("top_recommendation", "")
    if top_rec:
        md.append(top_rec)
    if top_ops:
        md += [
            "",
            "**Top 5 actions in priority order:**",
        ]
        for i, op in enumerate(top_ops[:5], 1):
            title = op.get("title", "")[:70]
            action = op.get("recommended_action", "")
            approval = " ⏳ Needs approval" if op.get("requires_ray_approval") else ""
            md.append(f"{i}. {title}{approval}")
            if action:
                md.append(f"   → {action}")
    md.append("")

    md += [
        "## Scouts Assigned",
        "",
    ]
    for scout in scouts_dispatched:
        md.append(f"- {scout}")
    if not scouts_dispatched:
        md.append("- No scouts dispatched in this cycle (dry run or no actionable sources).")
    md.append("")

    md += [
        "## Actions Created",
        "",
    ]
    try:
        from lib.hermes_action_queue import get_open_actions
        open_actions = get_open_actions()
        if open_actions:
            for a in open_actions[:5]:
                md.append(f"- [{a.status}] {a.title[:70]}")
        else:
            md.append("- No open actions yet.")
    except Exception:
        md.append("- (action queue unavailable)")
    md.append("")

    md += [
        "## Needs Ray Approval",
        "",
    ]
    if needs_approval:
        for item in needs_approval:
            md.append(f"- ⏳ {item.get('title','')[:70]} — {item.get('approval_reason','')}")
    else:
        md.append("- Nothing requires approval in this cycle.")
    md.append("")

    md += [
        "## What Will Happen Next",
        "",
        "If Ray approves (or no approval needed):",
    ]
    for op in top_ops[:3]:
        step = op.get("autonomous_next_step", op.get("recommended_action", ""))
        if step:
            md.append(f"  - {step}")
    md += [
        "",
        "Scheduler is NOT enabled. Ray must approve before daily automation starts.",
        "",
        "## Evidence Paths",
        "",
        f"- Intake report: {intake_results.get('md_path', '')}",
        f"- Intake JSON: {intake_results.get('artifact_path', '')}",
        f"- Decision report: {decision_results.get('md_path', '')}",
        f"- Top actions: {decision_results.get('top_actions_path', '')}",
        f"- Rejected: {decision_results.get('rejected_path', '')}",
        "",
        "## Telegram Digest Prepared",
        "",
        "```",
        telegram_message,
        "```",
    ]

    md_path.write_text("\n".join(md))

    # JSON artifact
    review_data = {
        "review_id": f"review_{ts}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intake_stats": intake_stats,
        "top_opportunities": top_ops[:10],
        "rejected": rejected[:10],
        "needs_approval": needs_approval,
        "scouts_dispatched": scouts_dispatched,
        "top_recommendation": top_rec,
        "intake_artifact_path": intake_results.get("artifact_path", ""),
        "decision_artifact_path": decision_results.get("artifact_path", ""),
    }
    json_path.write_text(json.dumps(review_data, indent=2))

    # Register artifacts
    try:
        from lib.nexus_artifact_registry import register_artifact
        register_artifact(
            agent_name="hermes_daily_monetization_digest",
            artifact_type="daily_research_review",
            file_path=str(md_path),
            title=f"Daily Research Review {ts}",
            description=f"Full review: {intake_stats.get('total',0)} sources, {len(top_ops)} actionable",
            evidence_level="verified_file",
        )
    except Exception:
        pass

    try:
        rel_md   = str(md_path.relative_to(ROOT))
        rel_json = str(json_path.relative_to(ROOT))
    except ValueError:
        rel_md   = str(md_path)
        rel_json = str(json_path)

    return rel_md, rel_json


def load_latest_digest_path() -> str:
    """Return path to the most recent daily research review markdown."""
    if not REVIEW_DIR.exists():
        return ""
    files = sorted(REVIEW_DIR.glob("daily_research_review_*.md"), reverse=True)
    if not files:
        return ""
    try:
        return str(files[0].relative_to(ROOT))
    except ValueError:
        return str(files[0])


def digest_plain_english(limit_ops: int = 5) -> str:
    """Return a plain-language summary of the latest daily digest for Telegram."""
    if not REVIEW_DIR.exists():
        return "No daily digest yet. Run: python3 scripts/run_daily_opportunity_intake.py --mode validation"

    files = sorted(REVIEW_DIR.glob("daily_research_review_*.json"), reverse=True)
    if not files:
        return "No daily digest yet. Run: python3 scripts/run_daily_opportunity_intake.py --mode validation"

    try:
        data = json.loads(files[0].read_text())
        total   = data.get("intake_stats", {}).get("total", 0)
        top_ops = data.get("top_opportunities", [])[:limit_ops]
        rejected = len(data.get("rejected", []))
        top_rec = data.get("top_recommendation", "")
        review_path = data.get("review_path", "")

        lines = [
            f"Latest daily digest ({files[0].name[:15]}):",
            f"  {total} sources reviewed, {len(top_ops)} actionable, {rejected} rejected.",
        ]
        if top_rec:
            lines.append(f"  Best move: {top_rec}")
        if top_ops:
            lines.append("  Top opportunities:")
            for op in top_ops[:3]:
                lines.append(f"    • {op.get('title','')[:60]} (score {op.get('monetization_score',0)})")
        lines.append(f"\nFull review: {data.get('intake_artifact_path','see docs/reports/review/')}")
        return "\n".join(lines)
    except Exception:
        return "Digest available but could not be read. Check docs/reports/review/"
