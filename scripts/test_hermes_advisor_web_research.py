#!/usr/bin/env python3
"""Hermes Advisor web research: safe handoff when browsing unavailable; no
fabricated facts; private context sanitized."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_advisor_web_research as WR  # noqa: E402


def main() -> int:
    fails = 0
    # 1. Default: no live web -> handoff with a drafted TheChoseone task, no results
    r = WR.research("best affiliate offers for funding checklist")
    ok = (r["mode"] == "handoff" and r["command_draft"].startswith("run web research")
          and r["results"] == [] and "can't browse" in r["message"].lower())
    fails += (not ok); print(f"{'✓' if ok else '✗FAIL'} no-live-web -> safe handoff (no fabricated facts)")

    # 2. Sanitization: private tokens/ids/accounts stripped from any query
    dirty = "affiliate offers chat_id=1288928049 token=abcdef goclearonline@gmail.com"
    clean = WR.sanitize_query(dirty)
    ok = "1288928049" not in clean and "token=" not in clean.lower() and "goclearonline" not in clean.lower()
    fails += (not ok); print(f"{'✓' if ok else '✗FAIL'} sanitize strips private context -> {clean!r}")

    # 3. Web disabled by default (no paid APIs / no silent external calls)
    ok = WR.web_enabled() is False
    fails += (not ok); print(f"{'✓' if ok else '✗FAIL'} live web disabled by default")

    # 4. Result template has citation + fact/recommendation fields
    t = WR.result_template()
    ok = all(k in t for k in ("title", "url", "source_date", "confidence", "fact_vs_recommendation"))
    fails += (not ok); print(f"{'✓' if ok else '✗FAIL'} result template is citation-first")

    print(f"\n=== web research · {fails} failures ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
