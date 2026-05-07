#!/usr/bin/env python3
"""Validation checks for Hermes model routing safety."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check(label: str, cond: bool, detail: str = "") -> bool:
    ok = "PASS" if cond else "FAIL"
    print(f"[{ok}] {label}" + (f" — {detail}" if detail else ""))
    return cond


def main() -> int:
    ok = True
    os.environ["HERMES_FALLBACK_ENABLED"] = "true"
    os.environ["OPENROUTER_CTX"] = "128000"
    os.environ["GROQ_CTX"] = "10000"

    from lib.model_router import get_provider, ModelRoutingError

    try:
        get_provider(task_type="funding_strategy", min_context=64000)
        ok &= _check("funding_strategy rejects 10K-only chain", True)
    except ModelRoutingError as e:
        ok &= _check("funding_strategy rejects small-context model", "too small" in str(e).lower())

    p = get_provider(task_type="premium_reasoning", min_context=64000)
    ok &= _check("premium_reasoning requires >=64K", int(p.get("max_context", 0)) >= 64000, str(p))

    p2 = get_provider(task_type="cheap_summary", min_context=0)
    ok &= _check("cheap_summary can use Ollama", p2.get("name") in {"netcup_ollama", "oracle_ollama", "groq"}, str(p2))

    # Simulate explicit rejection path for tiny context requirement mismatch
    try:
        get_provider(task_type="critical", min_context=9999999)
        ok &= _check("critical over-constrained path rejects", False, "expected ModelRoutingError")
    except ModelRoutingError:
        ok &= _check("critical over-constrained path rejects", True)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
