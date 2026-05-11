#!/usr/bin/env python3
"""Safety tests for Ops Monitor controlled activation."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    os.environ["OPS_MONITOR_AGENT_ENABLED"] = "true"
    os.environ["OPS_MONITOR_READ_ONLY"] = "true"
    os.environ["SWARM_EXECUTION_ENABLED"] = "false"
    os.environ["SWARM_DRY_RUN"] = "true"

    from lib.ops_monitor_agent import run_ops_monitor_summary
    from lib.swarm_coordinator import AGENT_REGISTRY

    sent = {"count": 0, "subject": "", "body": ""}

    def _fake_send(subject: str, body: str) -> None:
        sent["count"] += 1
        sent["subject"] = subject
        sent["body"] = body

    result = run_ops_monitor_summary(send_report_email=_fake_send)
    summary = result.get("summary") or {}

    ok &= check("ops monitor enabled flag works", result.get("ok") is True)
    ok &= check("ops monitor is read-only", result.get("read_only") is True and result.get("can_execute") is False)
    ok &= check("swarm execution remains disabled globally", result.get("dry_run_only") is True)
    ok &= check("full report routes to email path", sent["count"] == 1 and "Nexus Ops Monitor Summary" in sent["subject"])
    ok &= check("ops monitor summary includes worker status", isinstance(summary.get("worker_status_summary"), dict))
    ok &= check("ops monitor summary includes queue status", isinstance(summary.get("queue_summary"), dict))
    ok &= check("ops monitor summary includes pending approvals", isinstance(summary.get("pending_approvals"), list))

    ops = AGENT_REGISTRY.get("ops_monitor") or {}
    blocked = set(ops.get("requires_approval_for") or [])
    ok &= check("ops monitor cannot deploy/migrate/config/delete", "deploy" in blocked and "config_change" in blocked and "delete" in blocked)
    ok &= check("ops monitor cannot send Telegram directly", bool(ops.get("telegram_allowed")) is False)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
