#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.swarm_coordinator import list_agents, dry_run_swarm_plan, assign_task_to_agent


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    agents = list_agents()
    names = {a.get("name") for a in agents}
    required = {
        "Ops Monitor Agent",
        "Telegram/Comms Agent",
        "Funding Strategy Agent",
        "Credit Workflow Agent",
        "Grants Research Agent",
        "Business Setup Agent",
        "CRM Follow-up Agent",
        "Trading Research Agent",
        "QA/Test Agent",
        "Report Writer Agent",
    }
    ok &= check("list_agents returns all required roles", required.issubset(names))

    plan = dry_run_swarm_plan("Run funding strategy review and prepare recommendation")
    ok &= check("dry_run_swarm_plan returns dry run", bool(plan.get("dry_run")) and not bool(plan.get("can_execute")))
    ok &= check("dry_run_swarm_plan assigns agent", bool(plan.get("assigned_role")))

    risky = dry_run_swarm_plan("Deploy production config migration")
    ok &= check("risky swarm action requires approval", bool(risky.get("approval_required")))
    ok &= check("swarm max attempts set", int(risky.get("max_attempts", 0)) == 2)
    ok &= check("duplicate suppression enabled", bool(risky.get("duplicate_error_suppression")))

    direct = assign_task_to_agent("Send Telegram blast", "telegram_comms")
    ok &= check("swarm agents cannot send Telegram directly", not bool(direct.get("telegram_send_allowed", True)))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
