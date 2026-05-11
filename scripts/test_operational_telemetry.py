#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib import hermes_operational_telemetry as hot


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    rows = [
        {"payload": {"domain": "telegram", "event_name": "telegram_inbound", "duration_ms": 10, "command": "status"}},
        {"payload": {"domain": "telegram", "event_name": "telegram_reply_success", "duration_ms": 30, "command": "status"}},
        {"payload": {"domain": "telegram", "event_name": "telegram_timeout", "duration_ms": 1200, "command": "run qa check"}},
        {"payload": {"domain": "workers", "event_name": "worker_timeout_detected", "duration_ms": 1400}},
        {"payload": {"domain": "workers", "event_name": "worker_timeout_detected", "duration_ms": 1600}},
        {"payload": {"domain": "telegram", "event_name": "telegram_fallback_response", "command": "status"}},
        {"payload": {"domain": "telegram", "event_name": "telegram_duplicate_reply_suppressed", "command": "status"}},
        {"payload": {"domain": "telegram", "event_name": "telegram_failed_command", "command": "run qa check"}},
        {"payload": {"domain": "knowledge", "event_name": "knowledge_cache_hit", "category": "funding", "source_type": "workflow_outputs"}},
        {"payload": {"domain": "knowledge", "event_name": "knowledge_cache_miss", "category": "funding", "source_type": "system_events"}},
        {"payload": {"domain": "knowledge", "event_name": "knowledge_ranking_timing", "duration_ms": 18}},
        {"payload": {"domain": "knowledge", "event_name": "knowledge_retrieval_timing", "duration_ms": 22}},
        {"payload": {"domain": "knowledge", "event_name": "knowledge_compact_summary_timing", "duration_ms": 11}},
        {"payload": {"domain": "knowledge", "event_name": "knowledge_prior_success_weight_used"}},
    ]

    orig_rows = hot._telemetry_rows
    orig_select = hot._safe_select
    hot._telemetry_rows = lambda start, end: rows
    hot._safe_select = lambda path, timeout=8: [
        {"status": "stale", "worker_id": "w1", "last_seen_at": "2026-05-09T00:00:00+00:00"},
        {"status": "stale", "worker_id": "w2", "last_seen_at": "2026-05-09T00:00:00+00:00"},
    ] if path.startswith("worker_heartbeats") else [
        {"status": "completed", "payload": {"role": "credit_analyst"}},
        {"status": "failed", "payload": {"role": "credit_analyst", "reason": "timeout"}},
        {"status": "rejected", "payload": {"role": "credit_analyst", "reason": "unsupported_task_type"}},
    ] if "ceo_routed_worker_audit" in path else []

    try:
        tg = hot.telegram_reliability_rollup("2026-05-09")
        ok &= check("telegram inbound count", tg.get("inbound_count") == 1)
        ok &= check("telegram timeout count", tg.get("timeout_count") == 1)
        ok &= check("telegram avg latency", int(tg.get("avg_response_latency_ms") or 0) > 0)
        ok &= check("telegram per-command success tracked", int((((tg.get("per_command") or {}).get("status") or {}).get("success") or 0)) == 1)

        km = hot.knowledge_metrics_rollup("2026-05-09")
        ok &= check("knowledge cache hit tracked", km.get("cache_hit") == 1)
        ok &= check("knowledge cache miss tracked", km.get("cache_miss") == 1)
        ok &= check("knowledge timing tracked", int(km.get("ranking_latency_ms_avg") or 0) > 0)
        ok &= check("knowledge cache ratio tracked", float(km.get("cache_hit_ratio") or 0.0) > 0.0)
        ok &= check("knowledge debug trace generated", isinstance(km.get("debug_trace"), list) and len(km.get("debug_trace") or []) >= 1)

        wr = hot.worker_reliability_rollup("2026-05-09")
        ok &= check("worker success/failure tracked", wr.get("success_count") == 1 and wr.get("failure_count") == 1)
        ok &= check("worker unsupported route tracked", wr.get("unsupported_route_attempts") == 1)
        ok &= check("worker stale heartbeat tracked", wr.get("stale_worker_heartbeats") == 2)
        ok &= check("worker repeated timeout pattern detected", wr.get("repeated_timeout_pattern") is True)

        summary = hot.build_operational_summary(mode="detailed")
        safety = summary.get("safety") or {}
        ok &= check("operational summary has safety posture", safety.get("swarm_execution_enabled") is False and safety.get("autonomous_execution") is False)
        compact = hot.build_operational_summary(mode="compact")
        ok &= check("operational summary compact mode", "executive_delta" not in compact and isinstance(compact.get("telegram_reliability"), dict))
    finally:
        hot._telemetry_rows = orig_rows
        hot._safe_select = orig_select

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
