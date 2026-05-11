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
    r2 = try_internal_first("What funding blockers do we have?")
    ok &= check("funding routes internal-first", r2 is not None and r2.matched_topic == "funding")
    r3 = try_internal_first("Tell me a random joke")
    ok &= check("non-matching query falls through", r3 is None)
    r4 = try_internal_first("Summarize NotebookLM intake queue")
    ok &= check("notebooklm routes internal-first", r4 is not None and r4.matched_topic == "notebooklm")
    r5 = try_internal_first("What marketing research is pending?")
    ok &= check("marketing routes internal-first", r5 is not None and r5.matched_topic == "marketing")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
