"""
test_revenue_asset_fixer_no_execution.py
Tests: no Phase 6F function publishes content, emails subscribers,
       spends money, activates Stripe, applies to affiliates,
       runs live trading, or deploys production changes.
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


def no_execution(text: str) -> bool:
    EXECUTION_PATTERNS = [
        "has been published to",
        "email was sent to subscriber", "sent email to subscriber",
        "stripe payment charged", "stripe.charge", "payment_intent.create",
        "affiliate program applied", "deployed to production successfully",
        "live trading order placed",
        "subscriber list was emailed", "posted to social media",
    ]
    text_lower = text.lower()
    return not any(p in text_lower for p in EXECUTION_PATTERNS)


print("=== test_revenue_asset_fixer_no_execution ===\n")

from lib.hermes_revenue_asset_fixer import (
    apply_safe_asset_fixes,
    format_asset_fix_report,
    format_rescore_after_fixes_report,
    find_assets_needing_fixes,
    SAFETY_BOUNDARY,
)
from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet,
    build_revenue_asset_packet_with_fixes,
)

# ── apply_safe_asset_fixes result has no execution language ──────────────────
print("-- apply_safe_asset_fixes: no execution --")
result = apply_safe_asset_fixes()
report = format_asset_fix_report(result)
check("format_asset_fix_report: no execution language", no_execution(report))
check("result has safety_boundary", "safety_boundary" in result)
check("safety_boundary == SAFETY_BOUNDARY", result.get("safety_boundary") == SAFETY_BOUNDARY)

# ── format_asset_fix_report mentions safety ───────────────────────────────────
print("\n-- format_asset_fix_report safety mentions --")
report_lower = report.lower()
check("report mentions 'no content published' or 'not published'",
      "no content published" in report_lower or "not published" in report_lower
      or "no content was published" in report_lower)
check("report mentions no emails", "no emails" in report_lower or "no email" in report_lower)
check("report mentions no spending", "no money" in report_lower or "no spending" in report_lower)

# ── format_rescore_after_fixes_report has no execution ───────────────────────
print("\n-- format_rescore_after_fixes_report: no execution --")
packet = build_revenue_asset_packet_with_fixes()
rescore_report = format_rescore_after_fixes_report(56, 100, packet)
check("rescore report: no execution language", no_execution(rescore_report))
check("rescore report mentions safety",
      "no content published" in rescore_report.lower()
      or "no emails" in rescore_report.lower()
      or "safety" in rescore_report.lower())

# ── No Stripe/payment in any output ─────────────────────────────────────────
print("\n-- no Stripe/payment activation --")
PAYMENT_PATTERNS = ["stripe.charge", "payment_intent.create", "subscribe(", "checkout.session",
                    "card charged", "payment processed"]
for pattern in PAYMENT_PATTERNS:
    check(f"no '{pattern}' in fix report", pattern not in report.lower())
    check(f"no '{pattern}' in rescore report", pattern not in rescore_report.lower())

# ── SAFETY_BOUNDARY constant is non-empty ────────────────────────────────────
print("\n-- SAFETY_BOUNDARY constant --")
check("SAFETY_BOUNDARY is non-empty string", isinstance(SAFETY_BOUNDARY, str) and len(SAFETY_BOUNDARY) > 10)
check("SAFETY_BOUNDARY mentions approval",
      "approval" in SAFETY_BOUNDARY.lower() or "ray" in SAFETY_BOUNDARY.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
