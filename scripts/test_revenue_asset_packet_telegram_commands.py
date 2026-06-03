"""
test_revenue_asset_packet_telegram_commands.py
Tests: all Phase 6D intents route correctly and return expected headers.
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

DUMP_MARKERS = [
    "artifact_inventory", "handoff dump", "Executive Memory",
    "I can answer from verified artifacts", "Strategic context from evidence",
    "Quality escalation", "═══", "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_revenue_asset_packet_telegram_commands ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# ── classify_intent routing ────────────────────────────────────────────────────
print("-- classify_intent routing --")
ROUTING_TESTS = [
    ("build revenue asset packet",           "build_revenue_asset_packet"),
    ("create revenue asset packet",          "build_revenue_asset_packet"),
    ("show revenue asset packet",            "show_revenue_asset_packet"),
    ("show latest revenue packet",           "show_revenue_asset_packet"),
    ("show launch-ready assets",             "show_launch_ready_assets"),
    ("show content awaiting approval",       "show_content_awaiting_approval"),
    ("show cta options",                     "show_cta_options"),
    ("show launch checklist",                "show_launch_checklist"),
    ("show approval checklist",              "show_approval_checklist"),
    ("generate approval candidates",         "generate_approval_candidates"),
    ("create approval items from packet",    "generate_approval_candidates"),
]
for phrase, expected in ROUTING_TESTS:
    intent, _, _ = classify_intent(phrase)
    check(f"[{phrase[:50]}] → {expected}", intent == expected)

# ── response headers and no dump ──────────────────────────────────────────────
print("\n-- response headers and no dump --")
RESPONSE_TESTS = [
    ("build revenue asset packet",           "REVENUE ASSET PACKET CREATED"),
    ("show revenue asset packet",            "NEXUS REVENUE ASSET PACKET"),
    ("show launch-ready assets",             "LAUNCH-READY ASSETS"),
    ("show content awaiting approval",       "CONTENT AWAITING APPROVAL"),
    ("show cta options",                     "CTA OPTIONS"),
    ("show launch checklist",                "LAUNCH CHECKLIST"),
    ("show approval checklist",              "APPROVAL CHECKLIST"),
    ("generate approval candidates",         "APPROVAL CANDIDATES GENERATED"),
]
for phrase, expected in RESPONSE_TESTS:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:45]}] starts with '{expected}'",
          resp.startswith(expected) or expected in resp[:80])
    check(f"[{phrase[:45]}] no dump markers", no_dump(resp))
    check(f"[{phrase[:45]}] no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"[{phrase[:45]}] no ═══", "═══" not in resp)

# ── safety language present ───────────────────────────────────────────────────
print("\n-- safety language in build command --")
resp_build = run_command("build revenue asset packet", source="cli")
check("build mentions safety", "safety" in resp_build.lower() or "no content published" in resp_build.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
