#!/usr/bin/env python3
"""Lightweight validation for infrastructure foundation changes."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    from lib.model_router import resolve_task_type, routing_preview, ModelRoutingError
    from lib.hermes_gate import _event_hash, _critical_event_hash

    ok &= _check("resolve funding_strategy -> premium_reasoning", resolve_task_type("funding_strategy") == "premium_reasoning")
    ok &= _check("resolve telegram_reply -> cheap_summary", resolve_task_type("telegram_reply") == "cheap_summary")
    ok &= _check("resolve coding_assistant -> coding", resolve_task_type("coding_assistant") == "coding")

    try:
        rp = routing_preview("funding_strategy", min_context=64000)
        ok &= _check("routing preview contains provider", bool(rp.get("provider")))
    except ModelRoutingError:
        ok &= _check("routing preview handles strict min context", True)

    h1 = _event_hash("evt", "same text")
    h2 = _event_hash("evt", "same text")
    ok &= _check("event hash deterministic", h1 == h2)

    c1 = _critical_event_hash("critical_ops_alert")
    c2 = _critical_event_hash("critical_ops_alert")
    ok &= _check("critical hash deterministic", c1 == c2)

    os.environ["TELEGRAM_MANUAL_ONLY"] = "true"
    os.environ["TELEGRAM_AUTO_REPORTS_ENABLED"] = "true"
    from lib.hermes_gate import _auto_reports_enabled
    ok &= _check("manual-only overrides auto reports", _auto_reports_enabled() is False)

    # ai_ops foundation should not crash when Supabase is unavailable
    from lib.ai_ops_foundation import track_model_usage, track_retry_event, track_worker_health
    old_url = os.environ.get("SUPABASE_URL")
    old_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    os.environ["SUPABASE_URL"] = ""
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
    ok &= _check("track_model_usage handles missing Supabase", isinstance(track_model_usage("cheap_summary", "x", "y", 1, True), bool))
    ok &= _check("track_retry_event handles missing Supabase", isinstance(track_retry_event("x", "Err", 1, 1), bool))
    ok &= _check("track_worker_health handles missing Supabase", isinstance(track_worker_health("w", "healthy"), bool))
    if old_url is not None:
        os.environ["SUPABASE_URL"] = old_url
    if old_key is not None:
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = old_key

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
