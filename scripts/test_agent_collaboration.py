#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.agent_collaboration import (
    plan_agent_collaboration,
    assign_collaboration_steps,
    dry_run_collaboration_plan,
    summarize_collaboration_plan,
    validate_collaboration_safety,
)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    os.environ["CONTROLLED_AGENT_COLLABORATION_ENABLED"] = "true"
    os.environ["SWARM_EXECUTION_ENABLED"] = "false"

    steps = assign_collaboration_steps("funding optimization")
    ok &= check("collaboration steps assigned", len(steps) >= 3)

    plan = plan_agent_collaboration("credit workflow review")
    ok &= check("collaboration plan created", plan.get("enabled") is True and isinstance(plan.get("steps"), list))
    ok &= check("plan remains dry-run non-executable", plan.get("dry_run_only") is True and plan.get("can_execute") is False)

    risky = dry_run_collaboration_plan("deploy production migration")
    ok &= check("risky collaboration requires approval", bool((risky.get("safety") or {}).get("approval_required")))

    safety = validate_collaboration_safety(plan)
    ok &= check("safe plan validates", isinstance(safety.get("safe"), bool))

    summary = summarize_collaboration_plan(plan)
    ok &= check("plan summary generated", "dry-run" in summary.lower())

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
