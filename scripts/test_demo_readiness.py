#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.demo_readiness import build_demo_readiness_report, run_demo_readiness_check


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    report = build_demo_readiness_report()
    ok &= check("demo readiness has score", isinstance(report.get("score"), int))
    ok &= check("demo readiness has status", isinstance(report.get("status"), str))
    ok &= check("demo readiness has checks", isinstance(report.get("checks"), list) and len(report.get("checks") or []) >= 5)
    ok &= check("demo readiness includes marketing inputs", isinstance(report.get("marketing_plan_inputs_needed"), dict))
    run = run_demo_readiness_check()
    ok &= check("run_demo_readiness_check stable", isinstance(run.get("next_action"), str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
