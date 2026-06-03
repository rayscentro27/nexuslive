"""
test_revenue_packet_offer_bridge.py
Tests: build_offer_bridge returns free/next_step/recurring tiers;
       each tier has name, format, cta, status, safety_note;
       no payment activation; SAFETY_BOUNDARY present.
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


print("=== test_revenue_packet_offer_bridge ===\n")

from lib.hermes_revenue_asset_packet import build_offer_bridge, SAFETY_BOUNDARY

# ── Three tiers present ───────────────────────────────────────────────────────
print("-- three bridge tiers --")
bridge = build_offer_bridge()
check("bridge is dict", isinstance(bridge, dict))
check("'free' tier present", "free" in bridge)
check("'next_step' tier present", "next_step" in bridge)
check("'recurring' tier present", "recurring" in bridge)

# ── Each tier has required fields ────────────────────────────────────────────
print("\n-- each tier has required fields --")
for tier_key in ("free", "next_step", "recurring"):
    tier = bridge[tier_key]
    check(f"[{tier_key}] has 'name'", "name" in tier)
    check(f"[{tier_key}] has 'format'", "format" in tier)
    check(f"[{tier_key}] has 'cta'", "cta" in tier)
    check(f"[{tier_key}] has 'status'", "status" in tier)
    check(f"[{tier_key}] has 'safety_note'", "safety_note" in tier)
    check(f"[{tier_key}] status == internal_draft", tier.get("status") == "internal_draft")

# ── Safety boundary present ───────────────────────────────────────────────────
print("\n-- safety boundary --")
check("bridge has safety_note", "safety_note" in bridge)
check("bridge has safety_boundary", "safety_boundary" in bridge)
check("safety_boundary == SAFETY_BOUNDARY", bridge["safety_boundary"] == SAFETY_BOUNDARY)
check("bridge has created_at", "created_at" in bridge)

# ── No active payment execution in tier data ─────────────────────────────────
print("\n-- no active payment execution in tiers --")
# Note: SAFETY_BOUNDARY itself mentions "activate Stripe" as a prohibition —
# we check that the tier fields themselves don't contain payment execution.
EXECUTION_PATTERNS = ["stripe.charge", "payment_intent.create", "charge(", "invoice("]
for tier_key in ("free", "next_step", "recurring"):
    tier_str = str(bridge.get(tier_key, {})).lower()
    for pattern in EXECUTION_PATTERNS:
        check(f"[{tier_key}] no '{pattern}'", pattern not in tier_str)

# ── Recurring tier does NOT activate Stripe ───────────────────────────────────
print("\n-- recurring tier: Stripe not activated --")
recurring = bridge["recurring"]
rec_note = (recurring.get("safety_note") or "").lower()
check("recurring safety_note mentions no payment or no Stripe",
      "no payment" in rec_note or "no stripe" in rec_note or "requires ray" in rec_note)
check("free tier cta references download or checklist",
      "download" in bridge["free"].get("cta", "").lower()
      or "checklist" in bridge["free"].get("cta", "").lower()
      or "free" in bridge["free"].get("cta", "").lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
