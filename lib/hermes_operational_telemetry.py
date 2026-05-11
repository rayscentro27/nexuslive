from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import time


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day_range(day: str | None = None) -> tuple[str, str]:
    if day:
        dt = datetime.fromisoformat(f"{day}T00:00:00+00:00")
    else:
        n = _now()
        dt = datetime(n.year, n.month, n.day, tzinfo=timezone.utc)
    end = dt + timedelta(days=1)
    return dt.isoformat(), end.isoformat()


def emit_metric(event_name: str, *, status: str = "completed", payload: dict[str, Any] | None = None) -> None:
    """Best-effort non-blocking telemetry event emission."""
    try:
        from lib.event_intake import submit_system_event

        submit_system_event(
            "hermes_operational_telemetry",
            status=status,
            payload={
                "event_name": (event_name or "unknown").strip() or "unknown",
                "recorded_at": _now().isoformat(),
                **(payload or {}),
            },
        )
    except Exception:
        return


def timer_ms(started_at: float) -> int:
    return max(0, int((time.time() - started_at) * 1000))


def _safe_select(path: str, timeout: int = 8) -> list[dict[str, Any]]:
    try:
        from scripts.prelaunch_utils import rest_select

        return rest_select(path, timeout=timeout) or []
    except Exception:
        return []


def _telemetry_rows(start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    return _safe_select(
        "system_events"
        "?select=id,status,created_at,payload"
        "&event_type=eq.hermes_operational_telemetry"
        f"&created_at=gte.{start_iso}"
        f"&created_at=lt.{end_iso}"
        "&order=created_at.desc&limit=1200"
    )


def _p(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    return payload if isinstance(payload, dict) else {}


def telegram_reliability_rollup(day: str | None = None) -> dict[str, Any]:
    start_iso, end_iso = _day_range(day)
    rows = _telemetry_rows(start_iso, end_iso)
    metrics = {
        "inbound_count": 0,
        "reply_success_count": 0,
        "timeout_count": 0,
        "fallback_count": 0,
        "duplicate_prevented_count": 0,
        "failed_command_count": 0,
        "avg_response_latency_ms": 0,
        "per_command": {},
    }
    latencies: list[int] = []
    for row in rows:
        payload = _p(row)
        if payload.get("domain") != "telegram":
            continue
        event_name = str(payload.get("event_name") or "")
        command = str(payload.get("command") or "unknown").strip() or "unknown"
        if command not in metrics["per_command"]:
            metrics["per_command"][command] = {"success": 0, "failed": 0, "timeout": 0}
        if event_name == "telegram_inbound":
            metrics["inbound_count"] += 1
        elif event_name == "telegram_reply_success":
            metrics["reply_success_count"] += 1
            metrics["per_command"][command]["success"] += 1
        elif event_name == "telegram_timeout":
            metrics["timeout_count"] += 1
            metrics["per_command"][command]["timeout"] += 1
        elif event_name == "telegram_fallback_response":
            metrics["fallback_count"] += 1
        elif event_name == "telegram_duplicate_reply_suppressed":
            metrics["duplicate_prevented_count"] += 1
        elif event_name == "telegram_failed_command":
            metrics["failed_command_count"] += 1
            metrics["per_command"][command]["failed"] += 1
        latency = payload.get("duration_ms")
        if isinstance(latency, (int, float)) and latency >= 0:
            latencies.append(int(latency))
    if latencies:
        metrics["avg_response_latency_ms"] = int(sum(latencies) / len(latencies))
    return {
        "date": start_iso[:10],
        **metrics,
    }


def knowledge_metrics_rollup(day: str | None = None) -> dict[str, Any]:
    start_iso, end_iso = _day_range(day)
    rows = _telemetry_rows(start_iso, end_iso)
    out = {
        "cache_hit": 0,
        "cache_miss": 0,
        "retrieval_latency_ms_avg": 0,
        "ranking_latency_ms_avg": 0,
        "compact_summary_latency_ms_avg": 0,
        "source_usage": {},
        "category_usage": {},
        "prior_success_weight_used": 0,
        "cache_hit_ratio": 0.0,
        "debug_trace": [],
    }
    retrieval: list[int] = []
    ranking: list[int] = []
    compact: list[int] = []
    for row in rows:
        payload = _p(row)
        if payload.get("domain") != "knowledge":
            continue
        event_name = str(payload.get("event_name") or "")
        if event_name == "knowledge_cache_hit":
            out["cache_hit"] += 1
        elif event_name == "knowledge_cache_miss":
            out["cache_miss"] += 1
        elif event_name == "knowledge_prior_success_weight_used":
            out["prior_success_weight_used"] += 1
        if event_name == "knowledge_retrieval_timing":
            v = payload.get("duration_ms")
            if isinstance(v, (int, float)):
                retrieval.append(int(v))
        if event_name == "knowledge_ranking_timing":
            v = payload.get("duration_ms")
            if isinstance(v, (int, float)):
                ranking.append(int(v))
        if event_name == "knowledge_compact_summary_timing":
            v = payload.get("duration_ms")
            if isinstance(v, (int, float)):
                compact.append(int(v))
        src = str(payload.get("source_type") or "").strip()
        if src:
            out["source_usage"][src] = int(out["source_usage"].get(src, 0)) + 1
        cat = str(payload.get("category") or "").strip()
        if cat:
            out["category_usage"][cat] = int(out["category_usage"].get(cat, 0)) + 1
        if event_name and len(out["debug_trace"]) < 20:
            out["debug_trace"].append(
                {
                    "event_name": event_name,
                    "category": cat or None,
                    "source_type": src or None,
                }
            )
    if retrieval:
        out["retrieval_latency_ms_avg"] = int(sum(retrieval) / len(retrieval))
    if ranking:
        out["ranking_latency_ms_avg"] = int(sum(ranking) / len(ranking))
    if compact:
        out["compact_summary_latency_ms_avg"] = int(sum(compact) / len(compact))
    total_cache = int(out["cache_hit"] + out["cache_miss"])
    if total_cache > 0:
        out["cache_hit_ratio"] = round(float(out["cache_hit"]) / float(total_cache), 4)
    out["debug_trace"].sort(key=lambda x: str(x.get("event_name") or ""))
    return out


def worker_reliability_rollup(day: str | None = None) -> dict[str, Any]:
    start_iso, end_iso = _day_range(day)
    rows = _safe_select(
        "system_events"
        "?select=id,status,created_at,payload"
        "&event_type=eq.ceo_routed_worker_audit"
        f"&created_at=gte.{start_iso}"
        f"&created_at=lt.{end_iso}"
        "&order=created_at.desc&limit=600"
    )
    success = failure = rejected = unsupported = 0
    role_counts: dict[str, int] = {}
    for row in rows:
        payload = _p(row)
        status = str(row.get("status") or "").lower()
        reason = str(payload.get("reason") or "").lower()
        role = str(payload.get("role") or "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
        if status == "completed":
            success += 1
        elif status in {"failed", "error"}:
            failure += 1
        elif status in {"rejected", "skipped"}:
            rejected += 1
        if reason == "unsupported_task_type":
            unsupported += 1

    heartbeats = _safe_select("worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=60")
    stale = [r for r in heartbeats if str(r.get("status") or "").lower() == "stale"]
    warnings: list[str] = []
    timeout_rows = _telemetry_rows(start_iso, end_iso)
    timeout_events = [
        r for r in timeout_rows
        if str(_p(r).get("event_name") or "") in {"worker_timeout_detected", "telegram_timeout"}
    ]
    repeated_timeout_pattern = len(timeout_events) >= 3
    if failure >= 5:
        warnings.append("Repeated worker failures detected; consider cooldown and manual review.")
    if unsupported >= 3:
        warnings.append("Unsupported routed task attempts are trending up; tighten task validation upstream.")
    if len(stale) >= 2:
        warnings.append("Multiple stale worker heartbeats detected; verify worker availability.")
    if repeated_timeout_pattern:
        warnings.append("Repeated timeout pattern detected; consider temporary cooldown and dependency health checks.")
    return {
        "success_count": success,
        "failure_count": failure,
        "rejected_count": rejected,
        "unsupported_route_attempts": unsupported,
        "stale_worker_heartbeats": len(stale),
        "worker_role_activity": role_counts,
        "repeated_timeout_pattern": repeated_timeout_pattern,
        "degraded_worker_warnings": warnings,
        "escalation_recommendation": warnings[0] if warnings else "No escalation required.",
    }


def executive_delta_report() -> dict[str, Any]:
    today = _now().date().isoformat()
    yesterday = (_now() - timedelta(days=1)).date().isoformat()
    tg_today = telegram_reliability_rollup(today)
    tg_yesterday = telegram_reliability_rollup(yesterday)
    worker_today = worker_reliability_rollup(today)
    worker_yesterday = worker_reliability_rollup(yesterday)
    q_today = _safe_select("job_queue?select=id,status,created_at&order=created_at.desc&limit=300")
    q_yesterday = _safe_select(
        "job_queue?select=id,status,created_at"
        f"&created_at=lt.{_day_range(today)[0]}"
        "&order=created_at.desc&limit=300"
    )
    queue_delta = len(q_today) - len(q_yesterday)

    workflow_rows = _safe_select("workflow_outputs?select=workflow_type,status,created_at&order=created_at.desc&limit=160")
    workflow_counts: dict[str, int] = {}
    fail_counts: dict[str, int] = {}
    for row in workflow_rows:
        w = str(row.get("workflow_type") or "unknown")
        workflow_counts[w] = workflow_counts.get(w, 0) + 1
        if str(row.get("status") or "").lower() in {"failed", "error"}:
            fail_counts[w] = fail_counts.get(w, 0) + 1
    top_workflows = sorted(workflow_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_failures = sorted(fail_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    focus = []
    if tg_today.get("timeout_count", 0) > tg_yesterday.get("timeout_count", 0):
        focus.append("Reduce Telegram timeout paths and prioritize fast command responses.")
    if worker_today.get("failure_count", 0) > worker_yesterday.get("failure_count", 0):
        focus.append("Investigate worker degradation and apply manual cooldowns where needed.")
    if queue_delta > 20:
        focus.append("Queue backlog is growing; review pending approvals and blocked tasks.")
    if not focus:
        focus.append("Maintain current reliability posture and monitor trend continuity.")

    return {
        "today": today,
        "yesterday": yesterday,
        "queue_growth_delta": queue_delta,
        "telegram_reliability_trend": {
            "today": tg_today,
            "yesterday": tg_yesterday,
        },
        "worker_degradation_trend": {
            "today": worker_today,
            "yesterday": worker_yesterday,
        },
        "most_active_workflows": [{"workflow_type": k, "count": v} for k, v in top_workflows],
        "failure_trends": [{"workflow_type": k, "failed": v} for k, v in top_failures],
        "recommended_focus_areas": focus,
    }


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def build_operational_summary(mode: str = "detailed") -> dict[str, Any]:
    """Reusable operational summary object for Hermes consumers."""
    day = _now().date().isoformat()
    detailed = {
        "timestamp": _now().isoformat(),
        "day": day,
        "telegram_reliability": telegram_reliability_rollup(day),
        "knowledge_metrics": knowledge_metrics_rollup(day),
        "worker_reliability": worker_reliability_rollup(day),
        "executive_delta": executive_delta_report(),
        "safety": {
            "swarm_execution_enabled": False,
            "autonomous_execution": False,
            "live_trading_execution": False,
        },
    }
    if str(mode).lower() == "compact":
        compact = {
            "timestamp": detailed["timestamp"],
            "day": detailed["day"],
            "telegram_reliability": {
                "inbound_count": detailed["telegram_reliability"].get("inbound_count", 0),
                "reply_success_count": detailed["telegram_reliability"].get("reply_success_count", 0),
                "timeout_count": detailed["telegram_reliability"].get("timeout_count", 0),
                "avg_response_latency_ms": detailed["telegram_reliability"].get("avg_response_latency_ms", 0),
            },
            "knowledge_metrics": {
                "cache_hit_ratio": detailed["knowledge_metrics"].get("cache_hit_ratio", 0.0),
                "retrieval_latency_ms_avg": detailed["knowledge_metrics"].get("retrieval_latency_ms_avg", 0),
                "ranking_latency_ms_avg": detailed["knowledge_metrics"].get("ranking_latency_ms_avg", 0),
            },
            "worker_reliability": {
                "failure_count": detailed["worker_reliability"].get("failure_count", 0),
                "stale_worker_heartbeats": detailed["worker_reliability"].get("stale_worker_heartbeats", 0),
                "repeated_timeout_pattern": detailed["worker_reliability"].get("repeated_timeout_pattern", False),
            },
            "safety": detailed["safety"],
        }
        return _json_safe(compact)
    return _json_safe(detailed)
