"""Approval-ready recommendation queue using owner_approval_queue."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

QUEUE_ACTION_TYPE = "chief_of_staff_recommendation"


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _confidence_band(approved: float, rejected: float, succeeded: float, failed: float) -> str:
    decision_samples = approved + rejected
    outcome_samples = succeeded + failed
    total_samples = decision_samples + outcome_samples
    if total_samples == 0:
        return "pending"
    if total_samples < 3:
        return "insufficient data"
    if outcome_samples < 3:
        return "baseline confidence"
    success_rate = succeeded / max(outcome_samples, 1.0)
    if success_rate >= 0.7 and outcome_samples >= 5:
        return "high confidence"
    return "emerging signal"


def _urgency_label(details: dict) -> str:
    expected_roi = _safe_float(details.get("expected_roi"), 1.0)
    launch_speed = _safe_float(details.get("estimated_launch_speed"), 5.0)
    automation = _safe_float(details.get("automation_potential"), 0.5)
    if expected_roi >= 2.0 and launch_speed >= 7:
        return "high"
    if automation >= 0.7 or expected_roi >= 1.4:
        return "medium"
    return "low"


def _score_display(final_score: float, band: str) -> str:
    if final_score <= 0 or band in {"pending", "insufficient data"}:
        return "Baseline score pending additional outcome history"
    return f"Composite score {round(final_score, 2)}"


def _sb(path: str, method: str = "GET", body: dict | None = None) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        method=method,
        data=(json.dumps(body).encode() if body is not None else None),
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            payload = json.loads(r.read())
            if isinstance(payload, list):
                return payload
            return [payload] if payload else []
    except Exception:
        return []


def _description_for(rec_type: str, title: str) -> str:
    return f"[{rec_type}] {title}"[:180]


def _scored_details(rec_type: str, details: dict | None = None) -> dict:
    d = dict(details or {})
    d.setdefault("confidence_score", _safe_float(d.get("confidence_score"), 0.65))
    d.setdefault("expected_roi", _safe_float(d.get("expected_roi"), 1.5))
    d.setdefault("estimated_startup_cost", _safe_float(d.get("estimated_startup_cost"), 3.0))
    d.setdefault("estimated_launch_speed", _safe_float(d.get("estimated_launch_speed"), 7.0))
    d.setdefault("automation_potential", _safe_float(d.get("automation_potential"), 0.7))
    d.setdefault("execution_difficulty", _safe_float(d.get("execution_difficulty"), 0.5))
    d.setdefault("strategic_alignment", _safe_float(d.get("strategic_alignment"), 0.7))
    d.setdefault("historical_performance_score", _safe_float(d.get("historical_performance_score"), 0.5))

    # Higher is better; cost and difficulty are inverse signals.
    d["composite_score"] = round(
        d["confidence_score"] * 0.15
        + d["expected_roi"] * 0.20
        + (10.0 - d["estimated_startup_cost"]) * 0.10
        + d["estimated_launch_speed"] * 0.10
        + d["automation_potential"] * 0.15
        + (1.0 - d["execution_difficulty"]) * 0.10
        + d["strategic_alignment"] * 0.15
        + d["historical_performance_score"] * 0.05,
        4,
    )
    d["recommendation_type"] = rec_type
    return d


def enqueue_recommendation(rec_type: str, title: str, rationale: str, details: dict | None = None) -> str | None:
    allowed = {
        "trading_experiment",
        "business_opportunity",
        "website_build_brief",
        "grant_action",
        "funding_action",
        "ops_action",
    }
    if rec_type not in allowed:
        return None

    desc = _description_for(rec_type, title)
    exists = _sb(
        "owner_approval_queue?status=eq.pending"
        f"&action_type=eq.{QUEUE_ACTION_TYPE}"
        f"&description=eq.{urllib.parse.quote(desc)}&select=id&limit=1"
    )
    if exists:
        return exists[0].get("id")

    row = {
        "action_type": QUEUE_ACTION_TYPE,
        "description": desc,
        "payload": {
            "recommendation_type": rec_type,
            "title": title,
            "rationale": rationale,
            "details": _scored_details(rec_type, details),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "priority": "normal",
        "requested_by": "hermes_chief_of_staff",
        "status": "pending",
    }
    rows = _sb("owner_approval_queue", method="POST", body=row)
    return rows[0].get("id") if rows else None


def list_recommendations(pending_only: bool = False, limit: int = 20) -> list[dict]:
    status_filter = "&status=eq.pending" if pending_only else ""
    return _sb(
        "owner_approval_queue?select=id,status,priority,description,payload,created_at,reviewed_at"
        f"&action_type=eq.{QUEUE_ACTION_TYPE}{status_filter}&order=created_at.desc&limit={limit}"
    )


def format_recommendations(pending_only: bool = False) -> str:
    items = list_recommendations(pending_only=pending_only)
    if not items:
        return "No recommendations found." if not pending_only else "No pending recommendations."
    title = "Pending Recommendations" if pending_only else "Recommendations"
    lines = [f"<b>{title} ({len(items)})</b>"]
    for item in items:
        payload = item.get("payload") or {}
        rtype = payload.get("recommendation_type", "unknown")
        t = payload.get("title", "untitled")
        rationale = str(payload.get("rationale") or "").strip()
        details = payload.get("details") or {}
        urgency = _urgency_label(details)
        confidence = _safe_float(details.get("confidence_score"), 0.0)
        lines.append(
            f"- [{item.get('id','')[:8]}] {rtype}: {t} ({item.get('status','?')}) | urgency: {urgency} | confidence: {round(confidence, 2)}"
        )
        if rationale:
            lines.append(f"  why now: {rationale[:140]}")
    lines.append("Use: approve recommendation <id> | reject recommendation <id>")
    return "\n".join(lines)


def _learning_stats() -> dict[str, dict[str, float]]:
    rows = _sb(
        "owner_approval_queue?select=status,payload,action_type&order=created_at.desc&limit=500"
        f"&action_type=eq.{QUEUE_ACTION_TYPE}"
    )
    by_type: dict[str, dict[str, float]] = {}
    for r in rows:
        payload = r.get("payload") or {}
        rt = str(payload.get("recommendation_type") or "unknown")
        s = by_type.setdefault(rt, {"approved": 0, "rejected": 0, "succeeded": 0, "failed": 0, "total": 0})
        status = str(r.get("status") or "").lower()
        s["total"] += 1
        if status == "approved":
            s["approved"] += 1
        elif status == "rejected":
            s["rejected"] += 1
        elif status in {"completed", "success", "succeeded"}:
            s["succeeded"] += 1
        elif status in {"failed", "error"}:
            s["failed"] += 1
    return by_type


def ranked_recommendations(limit: int = 20) -> list[dict]:
    items = list_recommendations(pending_only=True, limit=limit)
    learning = _learning_stats()
    ranked: list[dict] = []
    for i in items:
        payload = i.get("payload") or {}
        rt = str(payload.get("recommendation_type") or "unknown")
        details = payload.get("details") or {}
        base = _safe_float(details.get("composite_score"), 0.0)
        stats = learning.get(rt, {})
        approved = _safe_float(stats.get("approved"), 0)
        rejected = _safe_float(stats.get("rejected"), 0)
        succeeded = _safe_float(stats.get("succeeded"), 0)
        failed = _safe_float(stats.get("failed"), 0)
        approval_rate = approved / max(approved + rejected, 1.0)
        success_rate = succeeded / max(succeeded + failed, 1.0)
        learning_boost = (approval_rate * 0.1) + (success_rate * 0.2)
        final = round(base * (1.0 + learning_boost), 4)
        band = _confidence_band(approved, rejected, succeeded, failed)
        ranked.append({
            **i,
            "base_score": base,
            "learning_boost": round(learning_boost, 4),
            "final_score": final,
            "approval_rate": round(approval_rate, 3),
            "success_rate": round(success_rate, 3),
            "confidence_band": band,
        })
    ranked.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return ranked


def format_rankings(limit: int = 10) -> str:
    ranked = ranked_recommendations(limit=limit)
    if not ranked:
        return "No pending recommendations to rank."
    lines = ["<b>Recommendation Rankings</b>"]
    for idx, r in enumerate(ranked[:limit], 1):
        payload = r.get("payload") or {}
        rt = payload.get("recommendation_type", "unknown")
        title = payload.get("title", "untitled")
        rationale = payload.get("rationale", "")
        details = payload.get("details") or {}
        confidence = r.get("confidence_band", "pending")
        urgency = _urgency_label(details)
        impact = details.get("expected_roi")
        score = _score_display(_safe_float(r.get("final_score"), 0.0), confidence)
        lines.append(
            f"{idx}. [{str(r.get('id',''))[:8]}] {rt} — {title} | {score} | confidence: {confidence}"
        )
        lines.append(
            f"   Why: {rationale[:120] or 'Aligned with weekly execution priorities.'} "
            f"| Expected impact: ROI x{_safe_float(impact, 1.0)} "
            f"| Urgency: {urgency}"
        )
    lines.append("Learning model: recommendations rise as approve/success outcomes accumulate.")
    try:
        from ceo_agent.credit_funding_intelligence import credit_actions_work_best, funding_blockers
        from ceo_agent.client_success_intelligence import prioritize_this_week

        lines.append(f"Credit signal: {credit_actions_work_best()}")
        lines.append(f"Funding signal: {funding_blockers()}")
        lines.append(f"Client signal: {prioritize_this_week()}")
    except Exception:
        pass
    return "\n".join(lines)


def category_outcomes() -> str:
    stats = _learning_stats()
    if not stats:
        return "No recommendation outcome history yet."
    lines = ["<b>Recommendation Outcome Learning</b>"]
    for rt, s in sorted(stats.items()):
        appr = s["approved"]
        rej = s["rejected"]
        suc = s["succeeded"]
        fail = s["failed"]
        band = _confidence_band(appr, rej, suc, fail)
        lines.append(f"- {rt}: approved={int(appr)} rejected={int(rej)} succeeded={int(suc)} failed={int(fail)} | signal: {band}")
    return "\n".join(lines)


def _find_item(prefix_id: str) -> dict | None:
    rows = list_recommendations(pending_only=False, limit=100)
    for r in rows:
        rid = str(r.get("id") or "")
        if rid == prefix_id or rid.startswith(prefix_id):
            return r
    return None


def set_recommendation_status(prefix_id: str, status: str) -> str:
    item = _find_item(prefix_id)
    if not item:
        return f"Recommendation '{prefix_id}' not found."
    rid = item["id"]
    payload = item.get("payload") or {}
    details = payload.get("details") or {}
    normalized = str(status or "").lower()
    outcome_quality = "pending"
    if normalized in {"approved", "completed", "success", "succeeded"}:
        outcome_quality = "positive"
    elif normalized in {"rejected", "failed", "error"}:
        outcome_quality = "negative"
    details.update(
        {
            "approval_status": "approved" if normalized == "approved" else "rejected" if normalized == "rejected" else "pending",
            "execution_status": normalized,
            "outcome_quality": outcome_quality,
            "completion_timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendation_category": payload.get("recommendation_type") or "unknown",
            "repeatability_signal": _safe_float(details.get("historical_performance_score"), 0.0),
            "roi_estimate": _safe_float(details.get("expected_roi"), 0.0),
        }
    )
    payload["details"] = details
    rows = _sb(
        f"owner_approval_queue?id=eq.{rid}",
        method="PATCH",
        body={"status": status, "reviewed_at": datetime.now(timezone.utc).isoformat(), "payload": payload},
    )
    return f"Recommendation {rid[:8]} marked {status}."


def generate_plan_for(prefix_id: str) -> str:
    item = _find_item(prefix_id)
    if not item:
        return f"Recommendation '{prefix_id}' not found."
    payload = item.get("payload") or {}
    rtype = payload.get("recommendation_type", "unknown")
    title = payload.get("title", "Untitled")
    details = payload.get("details") or {}

    if rtype == "website_build_brief" or rtype == "business_opportunity":
        return "\n".join([
            "<b>Build Plan (Approval-Ready, No Deployment)</b>",
            f"Recommendation: {title}",
            "1) Validate niche/problem statement",
            "2) Draft landing page copy and wireframe",
            "3) Define offer + lead magnet + CTA flow",
            "4) Define required pages and analytics events",
            "5) Prepare QA checklist and review packet",
            "6) Submit for final owner approval before any build/deploy",
        ])

    if rtype == "trading_experiment":
        return "\n".join([
            "<b>Trading Experiment Plan (Approval-Ready, No Auto-Trade)</b>",
            f"Recommendation: {title}",
            "1) Define hypothesis and expected edge",
            "2) Backtest on last 6-12 months with fixed rules",
            "3) Measure win rate, PF, drawdown, consistency",
            "4) Compare against baseline strategy",
            "5) Run paper-trading shadow test",
            "6) Submit results + go/no-go recommendation for approval",
        ])

    return "\n".join([
        "<b>Action Plan (Approval-Ready)</b>",
        f"Recommendation: {title}",
        f"Type: {rtype}",
        "1) Validate data and objective",
        "2) Draft scoped execution checklist",
        "3) Review risks/dependencies",
        "4) Submit for final approval before execution",
    ])


def seed_default_recommendations() -> list[str]:
    """Create one actionable recommendation per required category if missing."""
    seeded: list[str] = []
    defaults = [
        ("trading_experiment", "Run next strategy A/B experiment", "Test tighter entry filter and reduced risk size on weakest strategy."),
        ("business_opportunity", "Prioritize top online business opportunity", "Select highest composite opportunity for rapid validation."),
        ("website_build_brief", "Generate website brief for top opportunity", "Prepare approval-ready site brief without deployment."),
        ("grant_action", "Advance nearest-deadline grants", "Prioritize grants with upcoming deadlines and high fit."),
        ("funding_action", "Advance top funding action", "Move highest-impact funding step from pipeline into execution checklist."),
        ("ops_action", "Resolve recurring failed automations", "Identify top repeated failures and create remediation checklist."),
    ]
    for rec_type, title, rationale in defaults:
        rid = enqueue_recommendation(rec_type, title, rationale)
        if rid:
            seeded.append(rid)
    return seeded
