#!/usr/bin/env python3
"""Tests for swarm planned-run approval queue state management."""

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
    from lib.swarm_approval_queue import (
        approve_planned_run,
        cancel_planned_run,
        create_planned_run,
        get_planned_run,
        list_planned_runs,
        reject_planned_run,
    )

    row = create_planned_run("funding_onboarding", requested_by="test-suite")
    ok &= check("planned run created", bool(row.get("planned_run_id")))
    run_id = row.get("planned_run_id", "")

    rows = list_planned_runs()
    ok &= check("planned run listed", any(r.get("planned_run_id") == run_id for r in rows))
    ok &= check("execution flags false", row.get("can_execute") is False and row.get("execution_mode") == "preview_only")

    approved = approve_planned_run(run_id, actor="approver")
    ok &= check("approve changes state", approved.get("approval_status") == "approved")
    ok &= check("approve state only", approved.get("can_execute") is False and approved.get("execution_mode") == "preview_only")

    bad = reject_planned_run(run_id, actor="approver", reason="cannot reject approved")
    ok &= check("invalid transition blocked", bad.get("error") == "invalid_transition")

    row2 = create_planned_run("grant_research", requested_by="test-suite")
    cancelled = cancel_planned_run(row2.get("planned_run_id", ""), actor="reviewer", reason="not needed")
    ok &= check("cancel transition works", cancelled.get("approval_status") == "cancelled")

    missing = get_planned_run("prun_missing")
    ok &= check("missing run safe", missing is None)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
