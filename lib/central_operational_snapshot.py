from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import os
from typing import Any


def build_central_operational_snapshot(*, rest_select, model_preview: list[dict] | None = None) -> dict[str, Any]:
    """Build a read-only, centralized operational snapshot payload."""

    def _safe(path: str) -> list[dict[str, Any]]:
        try:
            rows = rest_select(path) or []
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    transcript_rows = _safe(
        "transcript_queue?select=id,title,domain,source_type,status,created_at&order=created_at.desc&limit=200"
    )
    knowledge_rows = _safe(
        "knowledge_items?select=id,title,domain,status,quality_score,approved_at,created_at&order=created_at.desc&limit=250"
    )
    ticket_rows = _safe(
        "research_requests?select=id,department,status,priority,created_at,completed_at&order=created_at.desc&limit=200"
    )
    provider_rows = _safe(
        "provider_health?select=provider_name,status,avg_latency_ms,last_checked_at&order=provider_name"
    )
    opportunity_rows = _safe(
        "business_opportunities?select=id,created_at,score,title&order=created_at.desc&limit=120"
    )
    grant_rows = _safe(
        "grant_opportunities?select=id,created_at,score,title&order=created_at.desc&limit=120"
    )
    metric_rows = _safe(
        "performance_metrics?select=metric_type,value,created_at&order=created_at.desc&limit=200"
    )
    worker_rows = _safe(
        "worker_heartbeats?select=worker_id,status,last_seen_at,notes&order=last_seen_at.desc&limit=120"
    )
    scheduler_rows = _safe(
        "scheduler_runs?select=job_name,status,started_at,finished_at,error_message&order=started_at.desc&limit=120"
    )
    analytics_rows = _safe(
        "analytics_events?select=feature,event_name,created_at&order=created_at.desc&limit=200"
    )
    aggregate_rows = _safe(
        "hermes_aggregates?select=event_source,event_type,aggregated_summary,created_at&order=created_at.desc&limit=80"
    )
    strategy_rows = _safe(
        "strategies_catalog?select=id,name,asset_class,risk_level,ai_confidence,edge_health,is_active,updated_at&order=updated_at.desc&limit=80"
    )
    experiment_rows = _safe(
        "candidate_variants?select=id,status,channel,headline,created_at,updated_at&order=updated_at.desc&limit=120"
    )
    paper_journal_rows = _safe(
        "paper_trading_journal_entries?select=id,entry_status,opened_at,closed_at,asset_class,symbol&order=opened_at.desc&limit=200"
    )
    paper_outcome_rows = _safe(
        "paper_trading_outcomes?select=id,result_label,pnl_amount,pnl_percent,created_at&order=created_at.desc&limit=200"
    )

    tq_status = Counter(str(r.get("status") or "unknown") for r in transcript_rows)
    tq_source = Counter(str(r.get("source_type") or "unknown") for r in transcript_rows)
    ki_status = Counter(str(r.get("status") or "unknown") for r in knowledge_rows)
    tk_status = Counter(str(r.get("status") or "unknown") for r in ticket_rows)
    tk_dept = Counter(str(r.get("department") or "unknown") for r in ticket_rows)
    provider_status = Counter(str(r.get("status") or "unknown") for r in provider_rows)
    worker_status = Counter(str(r.get("status") or "unknown") for r in worker_rows)
    scheduler_status = Counter(str(r.get("status") or "unknown") for r in scheduler_rows)
    research_backlog = Counter(str(r.get("status") or "unknown") for r in ticket_rows)
    event_features = Counter(str(r.get("feature") or "unknown") for r in analytics_rows)
    outcome_labels = Counter(str(r.get("result_label") or "unknown") for r in paper_outcome_rows)
    experiment_status = Counter(str(r.get("status") or "unknown") for r in experiment_rows)

    learned_recent = []
    for row in knowledge_rows[:15]:
        learned_recent.append(
            {
                "title": row.get("title") or "Untitled",
                "domain": row.get("domain") or "unknown",
                "quality_score": row.get("quality_score") or 0,
                "created_at": row.get("created_at"),
            }
        )

    warnings: list[str] = []
    if tq_status.get("failed", 0) > 0:
        warnings.append(f"{tq_status.get('failed', 0)} transcript ingestion failures")
    if provider_status.get("offline", 0) > 0:
        warnings.append(f"{provider_status.get('offline', 0)} providers offline")
    if tk_status.get("needs_review", 0) > 0:
        warnings.append(f"{tk_status.get('needs_review', 0)} research tickets need review")
    if research_backlog.get("queued", 0) >= 10:
        warnings.append(f"{research_backlog.get('queued', 0)} research tickets queued")
    if scheduler_status.get("failed", 0) > 0:
        warnings.append(f"{scheduler_status.get('failed', 0)} scheduler runs failed")
    if outcome_labels.get("loss", 0) >= 10 and outcome_labels.get("loss", 0) > outcome_labels.get("win", 0):
        warnings.append("paper trading losses exceed wins in recent outcomes")
    if experiment_status.get("running", 0) > 10:
        warnings.append("high number of running business experiments")

    now_ts = datetime.now(timezone.utc).timestamp()

    ticket_aging = {
        "over_4h": 0,
        "over_24h": 0,
    }
    for row in ticket_rows:
        created_at = row.get("created_at")
        if not created_at:
            continue
        try:
            created_ts = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        age_hours = (now_ts - created_ts) / 3600
        if age_hours >= 4:
            ticket_aging["over_4h"] += 1
        if age_hours >= 24:
            ticket_aging["over_24h"] += 1

    recent_activity = []
    for row in analytics_rows[:15]:
        recent_activity.append(
            {
                "feature": row.get("feature") or "unknown",
                "event_name": row.get("event_name") or "unknown",
                "created_at": row.get("created_at"),
            }
        )

    retrieval_metrics = [
        {
            "metric_type": row.get("metric_type"),
            "value": row.get("value"),
            "created_at": row.get("created_at"),
        }
        for row in metric_rows[:20]
        if str(row.get("metric_type") or "").startswith("retrieval_")
    ]

    aggregate_errors = []
    for row in aggregate_rows[:20]:
        event_type = str(row.get("event_type") or "")
        if "error" in event_type or "retry" in event_type or "fail" in event_type:
            aggregate_errors.append(
                {
                    "event_source": row.get("event_source"),
                    "event_type": row.get("event_type"),
                    "created_at": row.get("created_at"),
                }
            )

    pnl_values: list[float] = []
    for row in paper_outcome_rows:
        try:
            pnl_values.append(float(row.get("pnl_amount") or 0.0))
        except Exception:
            continue

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in pnl_values:
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)

    sim_enabled = str(os.getenv("SIMULATED_TRADING_ENABLED", "false")).lower() in {"1", "true", "yes", "on"}
    auto_paper_enabled = str(os.getenv("AUTONOMOUS_PAPER_TRADING", "false")).lower() in {"1", "true", "yes", "on"}
    sim_mode_enabled = str(os.getenv("TRADING_SIMULATION_MODE", "false")).lower() in {"1", "true", "yes", "on"}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "ingestion": {
            "transcript_queue_total": len(transcript_rows),
            "transcript_queue_status": dict(tq_status),
            "source_type_summary": dict(tq_source),
            "ingestion_pressure": tq_status.get("queued", 0) + tq_status.get("pending", 0),
        },
        "knowledge": {
            "knowledge_items_total": len(knowledge_rows),
            "status_counts": dict(ki_status),
            "approval_counts": {
                "approved": ki_status.get("approved", 0),
                "proposed": ki_status.get("proposed", 0),
                "needs_review": ki_status.get("needs_review", 0),
            },
            "learned_recent": learned_recent,
        },
        "tickets": {
            "total": len(ticket_rows),
            "status_counts": dict(tk_status),
            "department_counts": dict(tk_dept),
            "aging": ticket_aging,
        },
        "workforce_states": {
            "total": len(worker_rows),
            "status_counts": dict(worker_status),
            "latest": worker_rows[:15],
        },
        "providers": {
            "total": len(provider_rows),
            "status_counts": dict(provider_status),
            "latest": provider_rows[:12],
        },
        "research_load": {
            "open_tickets": tk_status.get("submitted", 0)
            + tk_status.get("queued", 0)
            + tk_status.get("researching", 0)
            + tk_status.get("needs_review", 0),
            "status_counts": dict(research_backlog),
            "aging": ticket_aging,
        },
        "opportunities": {
            "recent_count": len(opportunity_rows),
            "top_recent": opportunity_rows[:8],
        },
        "grants": {
            "recent_count": len(grant_rows),
            "top_recent": grant_rows[:8],
        },
        "semantic_retrieval": {
            "metrics": retrieval_metrics,
            "routing_preview": model_preview or [],
        },
        "paper_trading": {
            "autonomous_paper_trading": auto_paper_enabled,
            "simulated_trading_enabled": sim_enabled,
            "trading_simulation_mode": sim_mode_enabled,
            "journal_entries_recent": len(paper_journal_rows),
            "outcomes_recent": len(paper_outcome_rows),
            "result_counts": dict(outcome_labels),
            "win_rate": (
                round((outcome_labels.get("win", 0) / max(1, outcome_labels.get("win", 0) + outcome_labels.get("loss", 0))) * 100, 2)
                if (outcome_labels.get("win", 0) + outcome_labels.get("loss", 0)) > 0
                else 0.0
            ),
            "net_pnl": round(sum(pnl_values), 2),
            "max_drawdown": round(max_drawdown, 2),
            "latest_journal": paper_journal_rows[:10],
            "latest_outcomes": paper_outcome_rows[:10],
        },
        "strategy_rankings": {
            "active_count": len([r for r in strategy_rows if bool(r.get("is_active"))]),
            "top_active": sorted(
                [r for r in strategy_rows if bool(r.get("is_active"))],
                key=lambda r: float(r.get("ai_confidence") or 0.0),
                reverse=True,
            )[:8],
        },
        "business_experiments": {
            "total_recent": len(experiment_rows),
            "status_counts": dict(experiment_status),
            "active_count": experiment_status.get("running", 0) + experiment_status.get("queued", 0),
            "recent": experiment_rows[:12],
        },
        "worker_activity": {
            "recent_events": recent_activity,
            "feature_counts": dict(event_features),
        },
        "scheduler_health": {
            "total_runs": len(scheduler_rows),
            "status_counts": dict(scheduler_status),
            "latest": scheduler_rows[:12],
        },
        "errors": aggregate_errors,
        "warnings": warnings,
    }
