#!/usr/bin/env python3
"""Validation for Hermes router anti-spam circuit breaker."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check(label: str, cond: bool) -> bool:
    ok = "PASS" if cond else "FAIL"
    print(f"[{ok}] {label}")
    return cond


def main() -> int:
    import hermes_claude_bot as h

    h._router_error_state.clear()
    key = "ModelRoutingError:test"
    first = h._should_alert_router_error(key)
    second = h._should_alert_router_error(key)
    third = h._should_alert_router_error(key)

    ok = True
    ok &= _check("first router error alerts", first is True)
    ok &= _check("second router error suppressed", second is False)
    ok &= _check("third router error suppressed", third is False)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
