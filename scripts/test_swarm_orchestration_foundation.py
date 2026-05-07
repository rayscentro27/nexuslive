#!/usr/bin/env python3
"""Tests for safe swarm orchestration foundation (preview-only)."""

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
    from lib.swarm_orchestration_foundation import build_swarm_preview, get_allowed_delegates, list_handoff_rules

    rules = list_handoff_rules()
    ok &= check("handoff rules load", isinstance(rules, dict) and "ceo_router" in rules)

    delegates = get_allowed_delegates("ceo_router")
    ok &= check("delegates listed", isinstance(delegates, list) and len(delegates) > 0)

    preview = build_swarm_preview("ceo_router", "safe plan")
    ok &= check("preview has task sequence", isinstance(preview.get("task_sequence"), list))
    ok &= check("approval required by default", preview.get("approval_required") is True)
    ok &= check("execution disabled", preview.get("can_execute") is False)

    bad = build_swarm_preview("invalid_role", "bad")
    ok &= check("invalid initiator blocked", bad.get("status") == "blocked")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
