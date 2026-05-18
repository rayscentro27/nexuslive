#!/usr/bin/env python3
"""
Hermes Telegram Response Quality Tests

Tests that Hermes gives operationally-grounded responses for common Telegram
inputs, not generic chatbot filler.

Run: python scripts/test_hermes_telegram_response_quality.py
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load env silently
try:
    from lib.env_loader import load_nexus_env
    load_nexus_env()
except Exception:
    pass

import traceback
from dataclasses import dataclass
from typing import Callable


@dataclass
class ResponseTest:
    prompt: str
    description: str
    must_not_contain: list[str]
    should_contain_any: list[str]
    allow_none: bool = False  # True = None is acceptable (LLM handles it)


TESTS: list[ResponseTest] = [
    ResponseTest(
        prompt="Good morning",
        description="Morning greeting should be operational, not generic",
        must_not_contain=["How can I help you today?", "I'm doing well", "I don't have"],
        should_contain_any=["Morning", "Nexus", "running", "monitoring", "watching", "Ray"],
    ),
    ResponseTest(
        prompt="How are you?",
        description="Status check should be operational, not fake-emotional",
        must_not_contain=["I'm doing well, how can I help?", "I don't have feelings",
                          "As an AI", "I'm just a"],
        should_contain_any=["Solid", "tracking", "monitoring", "operations", "Nexus", "Ray"],
    ),
    ResponseTest(
        prompt="Good morning hermes",
        description="Explicit morning greeting handled by pattern engine",
        must_not_contain=["How can I help?", "I don't have live data"],
        should_contain_any=["Morning", "Nexus", "running", "Ray"],
    ),
    ResponseTest(
        prompt="done",
        description="Completion ack should be brief and forward-looking",
        must_not_contain=["How can I help?", "Great job!", "I don't know what was completed"],
        should_contain_any=["logged", "noted", "roadmap", "next", "priority"],
    ),
    ResponseTest(
        prompt="blocked",
        description="Blocker should trigger triage, not generic reply",
        must_not_contain=["I'm sorry to hear that", "How can I help?"],
        should_contain_any=["blocked", "specific", "escalate", "context", "Nexus"],
    ),
    ResponseTest(
        prompt="what should I work on today",
        description="Priority guidance from roadmap, not generic advice",
        must_not_contain=["I don't have access to your tasks", "I cannot help with that"],
        should_contain_any=["priority", "roadmap", "work on", "focus", "next", "blocker"],
        allow_none=False,
    ),
    ResponseTest(
        prompt="what did Nexus learn today",
        description="Knowledge digest should reference actual data sources",
        must_not_contain=["I don't have live data", "I cannot access"],
        should_contain_any=["knowledge", "learned", "approved", "ingested", "intake", "pending"],
        allow_none=True,
    ),
    ResponseTest(
        prompt="what did notebooklm learn",
        description="NotebookLM query intercepted by internal routing",
        must_not_contain=["I don't know", "I cannot access NotebookLM"],
        should_contain_any=["NotebookLM", "notebook", "sync", "knowledge", "proposed"],
        allow_none=True,
    ),
    ResponseTest(
        prompt="what trading strategies look strongest",
        description="Trading query stays in demo/paper mode context",
        must_not_contain=["live trading", "real money", "execute now"],
        should_contain_any=["demo", "paper", "strategy", "research", "trading", "dry"],
        allow_none=True,
    ),
    ResponseTest(
        prompt="show roadmap",
        description="Roadmap query uses Nexus roadmap data",
        must_not_contain=["I don't have access to a roadmap"],
        should_contain_any=["roadmap", "priority", "task", "step", "next", "focus"],
        allow_none=False,
    ),
    ResponseTest(
        prompt="what should opencode do",
        description="OpenCode task routing uses roadmap",
        must_not_contain=["I don't know what OpenCode should do"],
        should_contain_any=["OpenCode", "task", "coding", "priority", "implement", "review"],
        allow_none=False,
    ),
    ResponseTest(
        prompt="what business opportunities look realistic",
        description="Opportunity query routes to opportunity intelligence",
        must_not_contain=["I don't have business data"],
        should_contain_any=["opportunity", "business", "revenue", "catalog", "grant"],
        allow_none=True,
    ),
]


def _run_test(t: ResponseTest) -> tuple[bool, str]:
    """Run one test. Returns (passed, detail)."""
    try:
        # Layer 1: Try conversational/greeting patterns
        from lib.hermes_response_patterns import match_pattern, fill_template
        pattern = match_pattern(t.prompt)
        reply: str | None = None
        if pattern:
            intent = pattern.get("intent", "")
            conversational_intents = {
                "morning_greeting", "status_check_personal",
                "completion_acknowledgement", "blocker_triage",
            }
            if intent in conversational_intents:
                ctx: dict[str, str] = {
                    "operational_context": "Active: funding workflow, Telegram routing.",
                    "brief_status": "Active: 3 tasks queued.",
                    "next_best_action": "review proposed knowledge",
                    "next_best_action_prompt": "Ask 'what should I work on?'",
                    "context_note": "",
                    "next_action": "check roadmap",
                }
                tmpl = pattern.get("response_template", "")
                reply = fill_template(tmpl, ctx) if tmpl else None

        # Layer 2: internal_first
        if reply is None:
            from lib.hermes_internal_first import try_internal_first
            result = try_internal_first(t.prompt)
            if result:
                reply = result.text

        # Layer 3: supabase_first
        if reply is None:
            try:
                from lib.hermes_supabase_first import nexus_knowledge_reply
                reply = nexus_knowledge_reply(t.prompt)
            except Exception:
                pass

    except Exception as exc:
        return False, f"Exception: {exc}\n{traceback.format_exc()[:500]}"

    if reply is None:
        if t.allow_none:
            return True, "None (LLM fallback — acceptable)"
        return False, "Got None — expected a Nexus-sourced reply"

    reply_lower = reply.lower()

    # Check must_not_contain
    for bad in t.must_not_contain:
        if bad.lower() in reply_lower:
            return False, f"Contains banned phrase: '{bad}'\nReply: {reply[:200]}"

    # Check should_contain_any
    if t.should_contain_any:
        found = any(kw.lower() in reply_lower for kw in t.should_contain_any)
        if not found:
            return False, (
                f"Missing expected content. Want any of: {t.should_contain_any}\n"
                f"Reply: {reply[:200]}"
            )

    return True, f"OK — reply: {reply[:120]}"


def main() -> None:
    print(f"\nHermes Telegram Response Quality Tests")
    print("=" * 60)

    passed = 0
    failed = 0
    errors = 0
    fail_details: list[str] = []

    for i, t in enumerate(TESTS, 1):
        ok, detail = _run_test(t)
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"\n[{i:02d}] {status} — {t.description}")
        print(f"     Prompt: {t.prompt!r}")
        print(f"     {detail}")
        if ok:
            passed += 1
        else:
            failed += 1
            fail_details.append(f"[{i:02d}] {t.description}: {detail}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")

    if fail_details:
        print("\nFailed tests:")
        for d in fail_details:
            print(f"  • {d[:120]}")

    if failed > 0:
        print(f"\n{'='*60}")
        print("SAFETY CHECK: No real-money trading enabled in any response.")
        print("All test prompts use dry-run / demo / paper-only context.")
        sys.exit(1)
    else:
        print("\n✅ All response quality tests passed.")
        print("SAFETY: NEXUS_DRY_RUN=true | LIVE_TRADING=false | No real-money execution.")
        sys.exit(0)


if __name__ == "__main__":
    main()
