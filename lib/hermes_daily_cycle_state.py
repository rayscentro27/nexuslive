"""
hermes_daily_cycle_state.py
============================
Unified state resolver for all daily opportunity cycle commands.

All daily Telegram commands (show rejected, show top actions, show daily review,
what did you find today, etc.) must read from the SAME latest cycle.

This module finds the latest cycle and loads consistent data across all handlers.
No handler should glob report directories independently — they call this module.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
INTAKE_DIR = ROOT / "docs" / "reports" / "intake"
DECISION_DIR = ROOT / "docs" / "reports" / "monetization"
REVIEW_DIR = ROOT / "docs" / "reports" / "review"


def _ts_from_path(p: Path) -> str:
    """Extract timestamp string from filename like foo_20260529_222011.json"""
    stem = p.stem
    parts = stem.rsplit("_", 2)
    if len(parts) >= 3:
        return "_".join(parts[-2:])
    return stem


def find_latest_daily_cycle() -> dict[str, Path | None]:
    """
    Find the most recent completed cycle by locating the latest review artifact
    and matching the decision + intake artifacts with the closest timestamp.

    Returns a dict of keys: review, decision, rejected, intake — each is a Path or None.
    """
    review_files = sorted(REVIEW_DIR.glob("daily_research_review_*.json"), reverse=True) if REVIEW_DIR.exists() else []
    decision_files = sorted(DECISION_DIR.glob("monetization_decision_cycle_*.json"), reverse=True) if DECISION_DIR.exists() else []
    rejected_files = sorted(DECISION_DIR.glob("rejected_opportunities_*.json"), reverse=True) if DECISION_DIR.exists() else []
    intake_files = sorted(INTAKE_DIR.glob("daily_opportunity_intake_*.json"), reverse=True) if INTAKE_DIR.exists() else []

    review_path = review_files[0] if review_files else None
    decision_path = decision_files[0] if decision_files else None
    rejected_path = rejected_files[0] if rejected_files else None
    intake_path = intake_files[0] if intake_files else None

    # If review exists, try to match decision + rejected to same timestamp
    if review_path and decision_files:
        review_ts = _ts_from_path(review_path)
        for f in decision_files:
            if review_ts in f.stem:
                decision_path = f
                break

    if review_path and rejected_files:
        review_ts = _ts_from_path(review_path)
        for f in rejected_files:
            if review_ts in f.stem:
                rejected_path = f
                break

    if review_path and intake_files:
        review_ts = _ts_from_path(review_path)
        for f in intake_files:
            if review_ts in f.stem:
                intake_path = f
                break

    return {
        "review": review_path,
        "decision": decision_path,
        "rejected": rejected_path,
        "intake": intake_path,
    }


def load_daily_cycle_summary() -> dict[str, Any]:
    """
    Load high-level counts from the latest cycle.
    Returns a dict with: total_sources, real_sources, fallback_sources,
    actionable, rejected, high_value, pending_approval, cycle_ts, has_data.
    """
    cycle = find_latest_daily_cycle()
    result: dict[str, Any] = {
        "has_data": False,
        "total_sources": 0,
        "real_sources": 0,
        "fallback_sources": 0,
        "actionable": 0,
        "rejected": 0,
        "high_value": 0,
        "pending_approval": 0,
        "cycle_ts": None,
        "top_opportunity": None,
    }

    if cycle["review"]:
        try:
            data = json.loads(cycle["review"].read_text())
            result["has_data"] = True
            result["cycle_ts"] = data.get("generated_at") or _ts_from_path(cycle["review"])
            # Support both flat fields and intake_stats-nested structure
            stats = data.get("intake_stats") or {}
            result["total_sources"] = (
                data.get("total_sources") or stats.get("total", 0)
            )
            result["actionable"] = (
                data.get("actionable_count") or stats.get("high_potential", 0)
            )
            rejected_list = data.get("rejected", [])
            result["rejected"] = (
                data.get("rejected_count") or len(rejected_list)
            )
            result["high_value"] = (
                data.get("high_value_count") or
                sum(1 for op in data.get("top_opportunities", []) if (op.get("monetization_score") or 0) >= 70)
            )
            result["pending_approval"] = (
                data.get("approval_required_count") or len(data.get("needs_approval", []))
            )
            top_ops = data.get("top_opportunities", [])
            if top_ops:
                result["top_opportunity"] = top_ops[0]
        except Exception:
            pass

    if not result["has_data"] and cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            result["has_data"] = bool(decisions)
            result["total_sources"] = len(decisions)
            result["actionable"] = sum(1 for d in decisions if d.get("status") not in ("reject", "watch"))
            result["rejected"] = sum(1 for d in decisions if d.get("status") == "reject")
            result["high_value"] = sum(1 for d in decisions if (d.get("monetization_score") or 0) >= 70)
            result["pending_approval"] = sum(1 for d in decisions if d.get("requires_ray_approval"))
            actionable = [d for d in decisions if d.get("status") not in ("reject", "watch")]
            if actionable:
                result["top_opportunity"] = actionable[0]
            result["cycle_ts"] = _ts_from_path(cycle["decision"])
        except Exception:
            pass

    return result


def load_rejected_sources(limit: int = 10) -> list[dict]:
    """
    Load rejected sources from the same cycle as the latest review.
    This ensures 'show rejected' and 'show daily review' report the same count.
    """
    cycle = find_latest_daily_cycle()

    # Prefer data embedded in the review artifact
    if cycle["review"]:
        try:
            data = json.loads(cycle["review"].read_text())
            rejected = data.get("rejected", [])
            if isinstance(rejected, list) and rejected:
                return rejected[:limit]
        except Exception:
            pass

    # Fall back to rejected_opportunities_*.json from matched cycle
    if cycle["rejected"]:
        try:
            rejected = json.loads(cycle["rejected"].read_text())
            if isinstance(rejected, list):
                return rejected[:limit]
        except Exception:
            pass

    # Last resort: latest decision cycle, filter by status
    if cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            return [d for d in decisions if d.get("status") == "reject"][:limit]
        except Exception:
            pass

    return []


def load_top_opportunities(limit: int = 5) -> list[dict]:
    """Load top actionable opportunities from the latest cycle."""
    cycle = find_latest_daily_cycle()

    if cycle["review"]:
        try:
            data = json.loads(cycle["review"].read_text())
            top = data.get("top_opportunities", [])
            if isinstance(top, list) and top:
                return top[:limit]
        except Exception:
            pass

    if cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            actionable = [d for d in decisions if d.get("status") not in ("reject", "watch")]
            actionable.sort(key=lambda d: d.get("monetization_score", 0), reverse=True)
            return actionable[:limit]
        except Exception:
            pass

    return []


def load_pending_sources(limit: int = 10) -> list[dict]:
    """Load sources that are registered but not yet fully processed."""
    cycle = find_latest_daily_cycle()
    if cycle["intake"]:
        try:
            data = json.loads(cycle["intake"].read_text())
            records = data if isinstance(data, list) else data.get("records", [])
            return [r for r in records if r.get("status") in ("pending", "registered", "queued")][:limit]
        except Exception:
            pass
    return []


def load_scout_assignments(limit: int = 10) -> list[dict]:
    """Load scout assignments from the latest cycle."""
    cycle = find_latest_daily_cycle()
    if cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            return [d for d in decisions if d.get("assigned_scout")][:limit]
        except Exception:
            pass
    return []


def format_daily_cycle_status_common_language() -> str:
    """
    Plain-English summary for Telegram. Shows what was found, what's actionable,
    and what needs attention. No raw technical output.
    """
    summary = load_daily_cycle_summary()
    if not summary["has_data"]:
        return (
            "No daily intake has run yet.\n"
            "Say: 'Hermes, run daily opportunity intake' to start."
        )

    lines = []
    ts = summary.get("cycle_ts") or "recent"
    lines.append(f"Latest cycle: {ts}")
    lines.append(f"Sources found: {summary['total_sources']} total — "
                 f"{summary['actionable']} actionable, {summary['rejected']} filtered out.")

    if summary["high_value"]:
        lines.append(f"High-value signals: {summary['high_value']} (score 70+).")

    top = summary.get("top_opportunity")
    if top:
        title = (top.get("title") or "")[:65]
        score = top.get("monetization_score", 0)
        lines.append(f"Best opportunity: {title} (score {score}).")

    if summary["pending_approval"]:
        lines.append(f"Needs your approval: {summary['pending_approval']} item(s).")

    lines.append("\nSay 'show top monetization actions' for details, or 'show rejected' to see filtered sources.")
    return "\n".join(lines)


def format_information_sources_common_language() -> str:
    """
    Common-language summary of where Hermes gets its information.
    Does NOT dump raw directory listings. Shows meaningful counts.
    """
    summary = load_daily_cycle_summary()
    lines = [
        "Hermes reads from verified sources only — no invented data.",
        "",
        "Where information comes from:",
        "  • YouTube channels and keyword searches (channel registry + config)",
        "  • GitHub trending tools (weekly research outputs)",
        "  • Keyword-based web research (when free API is available)",
        "  • Social trend fallback tasks (manual research tasks created when APIs unavailable)",
        "  • Monetization category scoring (7-dimension engine)",
        "  • Nexus operating memory (Supabase-backed system events)",
        "  • Knowledge emails (forwarded via Telegram intake)",
        "  • Scout research outputs (artifact registry)",
    ]

    if summary["has_data"]:
        lines.append("")
        lines.append(f"Last cycle: {summary['total_sources']} sources collected and scored.")
        if summary["actionable"]:
            lines.append(f"  {summary['actionable']} marked actionable.")
        if summary["rejected"]:
            lines.append(f"  {summary['rejected']} filtered out (low score or irrelevant).")

    lines.append("")
    lines.append("To see raw artifact paths, say: 'show technical details'.")
    return "\n".join(lines)
