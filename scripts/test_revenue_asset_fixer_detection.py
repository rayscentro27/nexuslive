"""
test_revenue_asset_fixer_detection.py
Tests: detect_missing_internal_marker, detect_missing_cta,
       detect_missing_compliance_note, detect_missing_revenue_connection,
       detect_unsafe_promise_language.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_revenue_asset_fixer_detection ===\n")

from lib.hermes_revenue_asset_fixer import (
    detect_missing_internal_marker,
    detect_missing_cta,
    detect_missing_compliance_note,
    detect_missing_revenue_connection,
    detect_unsafe_promise_language,
)

# ── detect_missing_internal_marker ───────────────────────────────────────────
print("-- detect_missing_internal_marker --")
check("empty text → missing", detect_missing_internal_marker("") is True)
check("no marker → missing", detect_missing_internal_marker("# Hello\nSome content.") is True)
check("with INTERNAL ONLY → not missing",
      detect_missing_internal_marker("> INTERNAL ONLY — Draft for Ray review.") is False)
check("with INTERNAL ONLY lowercase → not missing",
      detect_missing_internal_marker("> internal only — draft for ray review.") is False)

# ── detect_missing_cta ───────────────────────────────────────────────────────
print("\n-- detect_missing_cta --")
check("empty text → missing CTA", detect_missing_cta("") is True)
check("no CTA → missing", detect_missing_cta("Some article text.") is True)
check("'download' present → not missing", detect_missing_cta("Download the checklist.") is False)
check("'start your' present → not missing", detect_missing_cta("Start your funding readiness check.") is False)
check("'sign up' present → not missing", detect_missing_cta("Sign up for free.") is False)
check("'get your' present → not missing", detect_missing_cta("Get your free checklist.") is False)
check("'check your' present → not missing", detect_missing_cta("Check your readiness today.") is False)
check("'fix your' present → not missing", detect_missing_cta("Fix your funding gaps now.") is False)
check("'join' present → not missing", detect_missing_cta("Join Nexus today.") is False)

# ── detect_missing_compliance_note ───────────────────────────────────────────
print("\n-- detect_missing_compliance_note --")
check("empty → missing compliance", detect_missing_compliance_note("") is True)
check("no compliance → missing", detect_missing_compliance_note("# Some article") is True)
check("'compliance note' present → not missing",
      detect_missing_compliance_note("Compliance note: educational purposes only.") is False)
check("'educational purposes' present → not missing",
      detect_missing_compliance_note("This is for educational purposes only.") is False)
check("'individual results will vary' present → not missing",
      detect_missing_compliance_note("Individual results will vary.") is False)

# ── detect_missing_revenue_connection ────────────────────────────────────────
print("\n-- detect_missing_revenue_connection --")
check("empty → missing revenue connection", detect_missing_revenue_connection("") is True)
check("no connection → missing", detect_missing_revenue_connection("# Some article") is True)
check("'nexus revenue connection' → not missing",
      detect_missing_revenue_connection("Nexus revenue connection: this supports 30-day goal.") is False)
check("'30-day revenue goal' → not missing",
      detect_missing_revenue_connection("This supports the 30-Day Revenue Goal.") is False)
check("'funding readiness review' → not missing",
      detect_missing_revenue_connection("Into a Funding Readiness Review today.") is False)

# ── detect_unsafe_promise_language ───────────────────────────────────────────
print("\n-- detect_unsafe_promise_language --")
check("empty → no unsafe", detect_unsafe_promise_language("") == [])
check("'guarantee' → unsafe", len(detect_unsafe_promise_language("We guarantee results.")) > 0)
check("'guaranteed' → unsafe", len(detect_unsafe_promise_language("Guaranteed approval")) > 0)
check("'get approved every time' → unsafe",
      len(detect_unsafe_promise_language("You will get approved every time.")) > 0)
check("'100% approval' → unsafe",
      len(detect_unsafe_promise_language("100% approval rate guaranteed.")) > 0)
check("compliance disclaimer 'does not guarantee' → caught",
      len(detect_unsafe_promise_language("This does not guarantee results")) > 0)
check("clean text → no unsafe",
      detect_unsafe_promise_language("Learn how lenders evaluate funding readiness.") == [])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
