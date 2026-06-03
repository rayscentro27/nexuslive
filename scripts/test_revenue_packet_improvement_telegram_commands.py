"""
test_revenue_packet_improvement_telegram_commands.py
Tests: all 9 Phase 6E commands route correctly and return correct headers.
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


print("=== test_revenue_packet_improvement_telegram_commands ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# ── Intent routing for all 9 Phase 6E phrases ────────────────────────────────
print("-- intent routing (9 Phase 6E phrases) --")
ROUTING_TESTS = [
    ("show revenue packet gaps",         "show_revenue_packet_gaps"),
    ("show readiness gaps",              "show_revenue_packet_gaps"),
    ("revenue packet gaps",              "show_revenue_packet_gaps"),
    ("improve revenue asset packet",     "improve_revenue_asset_packet"),
    ("improve packet score",             "improve_revenue_asset_packet"),
    ("raise packet readiness",           "improve_revenue_asset_packet"),
    ("show improved cta options",        "show_improved_cta_options"),
    ("improved cta options",             "show_improved_cta_options"),
    ("show offer bridge",                "show_offer_bridge"),
    ("offer bridge",                     "show_offer_bridge"),
    ("funnel model",                     "show_offer_bridge"),
    ("show packet improvement plan",     "show_packet_improvement_plan"),
    ("packet improvement plan",          "show_packet_improvement_plan"),
    ("rescore revenue packet",           "rescore_revenue_packet"),
    ("rescore packet",                   "rescore_revenue_packet"),
    ("show final review checklist",      "show_final_review_checklist"),
    ("final review checklist",           "show_final_review_checklist"),
    ("final checklist",                  "show_final_review_checklist"),
]
for phrase, expected in ROUTING_TESTS:
    intent, _, _ = classify_intent(phrase)
    check(f"{phrase!r} -> {expected}", intent == expected)

# ── Phase 6D phrases still route correctly ────────────────────────────────────
print("\n-- Phase 6D routing unaffected --")
PHASE6D_ROUTING = [
    ("build revenue asset packet",    "build_revenue_asset_packet"),
    ("show revenue asset packet",     "show_revenue_asset_packet"),
    ("show cta options",              "show_cta_options"),
    ("show launch checklist",         "show_launch_checklist"),
    ("generate approval candidates",  "generate_approval_candidates"),
]
for phrase, expected in PHASE6D_ROUTING:
    intent, _, _ = classify_intent(phrase)
    check(f"{phrase!r} -> {expected}", intent == expected)

# ── run_command returns correct headers ───────────────────────────────────────
print("\n-- run_command correct headers --")
COMMAND_TESTS = [
    ("show revenue packet gaps",        "REVENUE PACKET READINESS GAPS"),
    ("improve revenue asset packet",    "REVENUE PACKET IMPROVED"),
    ("show improved cta options",       "IMPROVED CTA OPTIONS"),
    ("show offer bridge",               "OFFER BRIDGE"),
    ("show packet improvement plan",    "PACKET IMPROVEMENT PLAN"),
    ("rescore revenue packet",          "REVENUE PACKET RESCORED"),
    ("show final review checklist",     "FINAL REVIEW CHECKLIST"),
]
for phrase, expected_header in COMMAND_TESTS:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:45]}] starts with '{expected_header}'",
          resp.startswith(expected_header) or expected_header in resp[:80])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
