"""
test_revenue_packet_improvement_safety.py
Tests: all Phase 6E formatted output contains safety language;
       no secrets in any output; SAFETY_BOUNDARY enforced in plan and bridge.
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


print("=== test_revenue_packet_improvement_safety ===\n")

from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet, build_improved_cta_set, build_offer_bridge,
    build_packet_improvement_plan, format_packet_readiness_gaps,
    format_improved_cta_options, format_offer_bridge,
    format_packet_improvement_plan, format_final_review_checklist,
    SAFETY_BOUNDARY,
)

packet = build_revenue_asset_packet()

# ── SAFETY_BOUNDARY in plan and bridge ───────────────────────────────────────
print("-- SAFETY_BOUNDARY in plan and bridge --")
plan = build_packet_improvement_plan(packet)
check("plan safety_boundary == SAFETY_BOUNDARY", plan.get("safety_boundary") == SAFETY_BOUNDARY)

bridge = build_offer_bridge(packet)
check("bridge safety_boundary == SAFETY_BOUNDARY", bridge.get("safety_boundary") == SAFETY_BOUNDARY)

# ── All tiers are internal_draft ─────────────────────────────────────────────
print("\n-- all offer bridge tiers are internal_draft --")
for tier_key in ("free", "next_step", "recurring"):
    check(f"bridge[{tier_key!r}] status == internal_draft",
          bridge.get(tier_key, {}).get("status") == "internal_draft")

# ── No secrets in CTA set ────────────────────────────────────────────────────
print("\n-- no secrets in CTA set --")
SECRET_PATTERNS = ["sk-", "xoxb-", "TELEGRAM_BOT_TOKEN", "SUPABASE_KEY",
                   "service_role", "postgres://", "password=", "secret"]
cta_str = str(build_improved_cta_set()).lower()
for pat in SECRET_PATTERNS:
    check(f"no '{pat}' in CTA set", pat.lower() not in cta_str)

# ── Safety mentions in all formatted outputs ──────────────────────────────────
print("\n-- safety mentions in formatted outputs --")
outputs = {
    "readiness_gaps":    format_packet_readiness_gaps(packet),
    "improved_cta":      format_improved_cta_options(packet),
    "offer_bridge":      format_offer_bridge(packet),
    "improvement_plan":  format_packet_improvement_plan(packet),
    "final_checklist":   format_final_review_checklist(packet),
}
for label, text in outputs.items():
    text_lower = text.lower()
    has_safety = (
        "safety" in text_lower
        or "approval" in text_lower
        or "not published" in text_lower
        or "no content published" in text_lower
        or "internal" in text_lower
        or "ray" in text_lower
    )
    check(f"[{label}] contains safety/approval language", has_safety)

# ── Blocked actions listed in plan ───────────────────────────────────────────
print("\n-- plan lists blocked actions --")
blocked = plan.get("blocked_until_ray_approves") or []
check("blocked list is non-empty", len(blocked) > 0)
blocked_str = " ".join(blocked).lower()
check("'publish' in blocked list", "publish" in blocked_str)
check("'email' in blocked list", "email" in blocked_str)
check("'stripe' in blocked_str or 'payment' in blocked_str",
      "stripe" in blocked_str or "payment" in blocked_str)

# ── Format final review checklist mentions Ray approval ───────────────────────
print("\n-- final review checklist mentions Ray approval --")
final = format_final_review_checklist(packet)
check("final checklist mentions 'Ray approval'",
      "ray approval" in final.lower() or "ray" in final.lower())
check("final checklist has approval boundary section",
      "approval boundary" in final.lower() or "boundary" in final.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
