#!/usr/bin/env python3
"""Tests for swarm scenario selector registry and preview helpers."""

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
    from lib.swarm_scenarios import list_swarm_scenarios, get_swarm_scenario, build_scenario_preview

    rows = list_swarm_scenarios()
    ok &= check("scenario registry loads", isinstance(rows, list) and len(rows) >= 6)
    ok &= check("known scenario exists", get_swarm_scenario("funding_onboarding") is not None)
    ok &= check("invalid scenario fails safely", get_swarm_scenario("nope") is None)

    prev = build_scenario_preview("funding_onboarding")
    ok &= check("scenario preview expected shape", isinstance(((prev.get("swarm_preview") or {}).get("task_sequence")), list))
    bad = build_scenario_preview("nope")
    ok &= check("invalid preview safe", bad.get("error") == "scenario_not_found")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
