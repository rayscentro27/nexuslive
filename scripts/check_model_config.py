#!/usr/bin/env python3
"""Sanity checks for Hermes model defaults and routing safety."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(1)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    hb = read("hermes_claude_bot.py")
    mr = read("lib/model_router.py")

    if "GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')" in hb:
        fail("hermes_claude_bot.py still defaults GROQ_MODEL to llama-3.3-70b-versatile")
    ok("hermes_claude_bot.py does not default to 10K Groq model")

    if "OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat')" not in hb:
        fail("hermes_claude_bot.py missing expected OPENROUTER_MODEL default")
    ok("hermes_claude_bot.py uses deepseek-chat default")

    if "_OR_MDL  = os.getenv(\"OPENROUTER_MODEL\",    \"deepseek/deepseek-chat\")" not in mr:
        fail("lib/model_router.py does not default OpenRouter model to deepseek/deepseek-chat")
    ok("model_router.py defaults to deepseek/deepseek-chat")

    ctx_match = re.search(r'OPENROUTER_CTX",\s*"(\d+)"', mr)
    if not ctx_match or int(ctx_match.group(1)) < 64000:
        fail("model_router.py OpenRouter default context below 64000")
    ok("model_router.py OpenRouter context is >= 64000")

    main_guard = "HERMES_MIN_CONTEXT_MAIN\", \"64000\""
    if main_guard not in mr:
        fail("model_router.py missing HERMES_MIN_CONTEXT_MAIN guard")
    ok("model_router.py has Hermes main workflow minimum-context guard")

    if "llama-3.3-70b-versatile" in mr and "_GQ_MDL" in mr:
        warn("model_router.py still allows llama-3.3-70b-versatile via env override; ensure GROQ_MODEL is updated in runtime env")

    # Advisory-only checks for short-task worker files
    advisory_files = [
        "trading-engine/tournament_service.py",
        "research-engine/strategy_ranker.py",
        "signal_review/signal_reviewer.py",
        "autonomy/agents/strategy_agent.py",
        "research-engine/strategy_enhancer.py",
        "nexus_email_pipeline.py",
    ]
    for p in advisory_files:
        txt = read(p)
        if "llama-3.3-70b-versatile" in txt:
            warn(f"{p} still references llama-3.3-70b-versatile (non-Hermes-main warning)")

    ok("Model config checks complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
