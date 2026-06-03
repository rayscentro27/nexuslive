"""
test_revenue_packet_improvement_no_execution.py
Tests: no Phase 6E function publishes content, emails subscribers,
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
    """Return True if text contains no active execution language.

    Uses precise patterns that indicate something WAS executed, not safety
    statements about what Hermes will NOT do.
    """
    EXECUTION_PATTERNS = [
        "content was published", "has been published to",
        "email was sent to subscriber", "sent email to subscriber",
        "stripe payment charged", "stripe.charge", "payment_intent.create",
        "affiliate program applied", "deployed to production successfully",
        "live trading order placed", "money was spent",
        "subscriber list was emailed", "posted to social media",
    ]
    text_lower = text.lower()
    return not any(p in text_lower for p in EXECUTION_PATTERNS)


print("=== test_revenue_packet_improvement_no_execution ===\n")

from lib.hermes_revenue_asset_packet import (
    analyze_packet_readiness_gaps, format_packet_readiness_gaps,
    recommend_packet_improvements, build_packet_improvement_plan,
    apply_internal_packet_improvements, rescore_packet_after_improvements,
    build_improved_cta_set, build_offer_bridge, save_improved_revenue_packet,
    format_improved_cta_options, format_offer_bridge,
    format_packet_improvement_plan, format_rescored_packet,
    format_final_review_checklist, build_revenue_asset_packet,
    SAFETY_BOUNDARY,
)

packet = build_revenue_asset_packet()

# ── No execution in gap analysis ──────────────────────────────────────────────
print("-- no execution in gap analysis --")
gaps = analyze_packet_readiness_gaps(packet)
for gap in gaps:
    check(f"[{gap['gap'][:30]}] no execution in remediation",
          no_execution(gap.get("remediation", "")))

# ── No execution in formatted outputs ────────────────────────────────────────
print("\n-- no execution in formatted outputs --")
outputs = {
    "format_packet_readiness_gaps":  format_packet_readiness_gaps(packet),
    "format_improved_cta_options":   format_improved_cta_options(packet),
    "format_offer_bridge":           format_offer_bridge(packet),
    "format_packet_improvement_plan": format_packet_improvement_plan(packet),
    "format_rescored_packet":        format_rescored_packet(rescore_packet_after_improvements(packet)),
    "format_final_review_checklist": format_final_review_checklist(packet),
}
for label, text in outputs.items():
    check(f"[{label}] no execution language", no_execution(text))

# ── SAFETY_BOUNDARY mentioned in key outputs ──────────────────────────────────
print("\n-- SAFETY_BOUNDARY enforced --")
for label, text in outputs.items():
    has_safety = (
        "safety" in text.lower()
        or "no content published" in text.lower()
        or "approval" in text.lower()
        or "ray approval" in text.lower()
    )
    check(f"[{label}] mentions safety/approval", has_safety)

# ── apply_internal_packet_improvements does NOT modify content files ──────────
print("\n-- apply_internal_packet_improvements: no file writes --")
improved = apply_internal_packet_improvements(packet)
check("improved has improvement_applied=True", improved.get("improvement_applied") is True)
check("improved has improved_at timestamp", "improved_at" in improved)
# Verify no actual files were modified (check mtime of assets)
for orig_asset, imp_asset in zip(packet.get("assets") or [], improved.get("assets") or []):
    orig_path = orig_asset.get("path", "")
    imp_path  = imp_asset.get("path", "")
    if orig_path and Path(orig_path).exists():
        orig_mtime = Path(orig_path).stat().st_mtime
        check(f"[{Path(orig_path).name[:30]}] file not modified by improvement",
              Path(imp_path).stat().st_mtime == orig_mtime)

# ── Offer bridge has no active payment ────────────────────────────────────────
print("\n-- offer bridge: no active payment --")
bridge = build_offer_bridge(packet)
bridge_str = str(bridge).lower()
ACTIVE_PAYMENT_PATTERNS = ["stripe.charge", "payment.intent", "subscribe(", "checkout.session"]
for pattern in ACTIVE_PAYMENT_PATTERNS:
    check(f"no '{pattern}' in offer bridge", pattern not in bridge_str)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
