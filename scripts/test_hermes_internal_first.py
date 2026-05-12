#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.hermes_internal_first import try_internal_first


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    r1 = try_internal_first("What's going on with OpenCode?")
    ok &= check("opencode routes internal-first", r1 is not None and "Confidence:" not in r1.text and r1.confidence.startswith("INTERNAL_"))
    ok &= check("opencode reply has no 'Direct answer:' prefix", r1 is not None and not r1.text.startswith("Direct answer:"))

    r2 = try_internal_first("What funding blockers do we have?")
    ok &= check("funding routes internal-first", r2 is not None and r2.matched_topic == "funding")
    ok &= check("funding reply has no 'Direct answer:' prefix", r2 is not None and not r2.text.startswith("Direct answer:"))

    r3 = try_internal_first("Tell me a random joke")
    ok &= check("non-matching query falls through", r3 is None)

    r4 = try_internal_first("Summarize NotebookLM intake queue")
    ok &= check("notebooklm routes internal-first", r4 is not None and r4.matched_topic == "notebooklm")

    r5 = try_internal_first("What marketing research is pending?")
    ok &= check("marketing routes internal-first", r5 is not None and r5.matched_topic == "marketing")

    r6 = try_internal_first("What AI providers are available?")
    ok &= check("ai_providers routes internal-first", r6 is not None and r6.matched_topic == "ai_providers")
    ok &= check("ai_providers reply mentions OpenRouter", r6 is not None and "openrouter" in r6.text.lower())
    ok &= check("ai_providers reply does NOT mention DeepMind or Bard", r6 is not None and "deepmind" not in r6.text.lower() and "bard" not in r6.text.lower())

    r7 = try_internal_first("What should I focus on today?")
    ok &= check("'focus today' routes internal-first (today topic)", r7 is not None and r7.matched_topic == "today")

    r8 = try_internal_first("What should I work on today?")
    ok &= check("'work on today' routes internal-first (today topic)", r8 is not None and r8.matched_topic == "today")

    r9 = try_internal_first("Is Claude available?")
    ok &= check("'is claude available' routes to ai_providers", r9 is not None and r9.matched_topic == "ai_providers")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
