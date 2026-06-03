"""
test_revenue_asset_fixer_telegram_commands.py
Tests: Phase 6F intents route to correct handlers with proper response headers.
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


print("=== test_revenue_asset_fixer_telegram_commands ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# ── Intent classification ─────────────────────────────────────────────────────
print("-- intent classification --")

INTENT_MAP = {
    "fix revenue packet assets":              "fix_revenue_packet_assets",
    "apply safe asset fixes":                 "fix_revenue_packet_assets",
    "fix packet gaps":                        "fix_revenue_packet_assets",
    "fix revenue asset gaps":                 "fix_revenue_packet_assets",
    "clean revenue assets":                   "fix_revenue_packet_assets",
    "remove unsafe promises from assets":     "fix_revenue_packet_assets",
    "soften unsafe language":                 "fix_revenue_packet_assets",
    "add cta to revenue assets":              "fix_revenue_packet_assets",
    "add compliance notes to assets":         "fix_revenue_packet_assets",
    "show asset fix report":                  "show_asset_fix_report",
    "asset fix report":                       "show_asset_fix_report",
    "what was fixed":                         "show_asset_fix_report",
    "rescore after fixes":                    "rescore_after_fixes",
    "update score after fixes":               "rescore_after_fixes",
    "what is the score after fixes":          "rescore_after_fixes",
}

for phrase, expected_intent in INTENT_MAP.items():
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:45]}' → {expected_intent}", intent == expected_intent)

# ── Handler responses have correct headers ────────────────────────────────────
print("\n-- handler response headers --")

HEADER_MAP = {
    "fix revenue packet assets":  "REVENUE ASSET FIXES APPLIED",
    "show asset fix report":      ("REVENUE ASSET FIX REPORT", "REVENUE ASSET FIXES APPLIED"),
    "rescore after fixes":        "REVENUE PACKET RESCORED AFTER FIXES",
}

for phrase, expected_header in HEADER_MAP.items():
    try:
        response = run_command(phrase)
        response_upper = (response or "").upper()
        if isinstance(expected_header, tuple):
            has_header = any(h.upper() in response_upper for h in expected_header)
        else:
            has_header = expected_header.upper() in response_upper
        check(f"'{phrase[:40]}' has correct header", has_header)
    except Exception as exc:
        check(f"'{phrase[:40]}' did not raise", False)
        print(f"    Error: {exc!s:.100}")

# ── Safety language in responses ──────────────────────────────────────────────
print("\n-- safety language in responses --")

for phrase in ("fix revenue packet assets", "rescore after fixes"):
    try:
        response = (run_command(phrase) or "").lower()
        has_safety = (
            "no content published" in response
            or "no content was published" in response
            or "no emails" in response
            or "no money" in response
            or "safety" in response
        )
        check(f"'{phrase[:40]}' has safety language", has_safety)
    except Exception as exc:
        check(f"'{phrase[:40]}' safety check did not raise", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
