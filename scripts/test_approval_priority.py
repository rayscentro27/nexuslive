#!/usr/bin/env python3
"""Approval queue recommends Credit/Funding first (monetization priority), while
Top facts still reflect real size/status. Read-only."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import lib.hermes_command_reporter as R  # noqa: E402

fails = 0
def check(name, cond):
    global fails
    print(f"  {'✓' if cond else '✗FAIL'} {name}")
    fails += (not cond)

# Simulate: opportunity has the MOST assets, but credit must be recommended.
orig = R._needs_review_by_pkg
R._needs_review_by_pkg = lambda: Counter({"proof_opportunity": 52, "proof_credit": 39,
                                          "proof_trading": 39, "proof_funding": 26,
                                          "proof_ai_improvement": 26})
try:
    out = R.approval_queue()
    print(out)
    print("---")
    check("Top facts still include proof_opportunity (most assets)", "proof_opportunity" in out)
    check("Needs Ray recommends Credit Readiness Pack first", "Credit Readiness Pack first" in out)
    check("Needs Ray cites $97–$297 readiness offer", "$97–$297" in out)
    check("does NOT recommend proof_opportunity in Needs Ray",
          "Opportunity Pack first" not in out)
    check("approve command targets proof_credit",
          "approve all assets in package proof_credit with notes: Approved for manual use only." in out)
    check("revise command targets proof_credit + paid-review wording",
          "request revision for package proof_credit with notes: Make this more specific, practical, "
          "and ready for a paid readiness review." in out)
    check("show package proof_credit present", "show package proof_credit" in out)
    check("details approval queue present", "details approval queue" in out)
    check("safety: manual-use only, no auto publish/send/charge",
          "manual use" in out.lower() and "does NOT auto-publish, send, or charge" in out)

    # If credit absent, fall to funding next.
    R._needs_review_by_pkg = lambda: Counter({"proof_opportunity": 50, "proof_funding": 10})
    out2 = R.approval_queue()
    check("falls to Funding when credit absent", "Funding Readiness Pack first" in out2)
finally:
    R._needs_review_by_pkg = orig

print(f"\n=== {fails} failures ===")
sys.exit(1 if fails else 0)
