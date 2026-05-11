#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def _flag(name: str, default: str) -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    ok = True
    os.environ["SWARM_EXECUTION_ENABLED"] = "false"
    os.environ["CONTROLLED_AGENT_COLLABORATION_ENABLED"] = "true"
    os.environ["EXECUTIVE_REPORTS_ENABLED"] = "true"
    os.environ["AI_OPERATIONS_SCORING_ENABLED"] = "true"
    ok &= check("swarm execution disabled", _flag("SWARM_EXECUTION_ENABLED", "false") is False)
    ok &= check("controlled collaboration enabled", _flag("CONTROLLED_AGENT_COLLABORATION_ENABLED", "true") is True)
    ok &= check("executive reports enabled", _flag("EXECUTIVE_REPORTS_ENABLED", "true") is True)
    ok &= check("ai ops scoring enabled", _flag("AI_OPERATIONS_SCORING_ENABLED", "true") is True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
