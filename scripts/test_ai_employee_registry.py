#!/usr/bin/env python3
"""Tests for AI employee role registry foundation."""

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
    from lib.ai_employee_registry import list_roles, get_role, validate_role_task, role_routing_preview

    roles = list_roles()
    ok &= check("registry loads", isinstance(roles, list) and len(roles) >= 8)
    ok &= check("known role exists", get_role("ceo_router") is not None)
    ok &= check("invalid role fails safely", get_role("does_not_exist") is None)
    ok &= check("invalid role task fails safely", validate_role_task("does_not_exist", "cheap_summary") is False)
    ok &= check("invalid task for role fails safely", validate_role_task("credit_ai", "coding_assistant") is False)

    rp = role_routing_preview("credit_ai")
    ok &= check("role routing preview shape", isinstance(rp, dict) and "role_id" in rp)
    rp_bad = role_routing_preview("nope")
    ok &= check("invalid preview safe error", rp_bad.get("error") == "role_not_found")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
