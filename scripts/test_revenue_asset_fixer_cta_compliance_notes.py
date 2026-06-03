"""
test_revenue_asset_fixer_cta_compliance_notes.py
Tests: add_cta_section, add_compliance_note, add_revenue_connection_note
       insert near top so scorer window sees them.
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


print("=== test_revenue_asset_fixer_cta_compliance_notes ===\n")

from lib.hermes_revenue_asset_fixer import (
    add_cta_section,
    add_compliance_note,
    add_revenue_connection_note,
    add_internal_only_marker,
    detect_missing_cta,
    detect_missing_compliance_note,
    detect_missing_revenue_connection,
    _SCORER_READ_LIMIT,
    _INTERNAL_MARKER,
)

BASE = f"{_INTERNAL_MARKER}\n\n# Business Preparation Guide\n\nLearn how to strengthen your application profile.\n"

# ── add_cta_section ───────────────────────────────────────────────────────────
print("-- add_cta_section --")
for atype in ("lead_magnet", "checklist", "newsletter", "seo_article", "youtube_script",
              "linkedin_post", "x_post", "tiktok_hook", "other"):
    with_cta = add_cta_section(BASE, atype)
    window = with_cta[:_SCORER_READ_LIMIT]
    check(f"[{atype}] CTA present in window", detect_missing_cta(window) is False)

# ── add_cta_section idempotent ────────────────────────────────────────────────
print("\n-- add_cta_section idempotent --")
already = BASE + "\nCTA:\nDownload the free checklist.\n"
result = add_cta_section(already, "lead_magnet")
check("CTA not doubled if already present in window", result.count("CTA:") == 1)

# ── add_compliance_note ───────────────────────────────────────────────────────
print("\n-- add_compliance_note --")
with_comp = add_compliance_note(BASE, "seo_article")
window_comp = with_comp[:_SCORER_READ_LIMIT]
check("compliance note in window", detect_missing_compliance_note(window_comp) is False)
check("compliance text present", "educational purposes" in with_comp.lower())

# ── add_compliance_note idempotent ────────────────────────────────────────────
print("\n-- add_compliance_note idempotent --")
already_comp = BASE + "\nCompliance note: Educational purposes only. Individual results will vary.\n"
result_comp = add_compliance_note(already_comp, "seo_article")
check("compliance not doubled", result_comp.count("Compliance note") <= 1
      or result_comp.lower().count("educational purposes") == 1)

# ── add_revenue_connection_note ───────────────────────────────────────────────
print("\n-- add_revenue_connection_note --")
with_rev = add_revenue_connection_note(BASE, "lead_magnet")
window_rev = with_rev[:_SCORER_READ_LIMIT]
check("revenue connection in window", detect_missing_revenue_connection(window_rev) is False)
check("30-day revenue goal mentioned", "30-day revenue" in with_rev.lower()
      or "30-day goal" in with_rev.lower())

# ── Inserted after internal marker, not mid-line ──────────────────────────────
print("\n-- insertions after internal marker (not mid-line) --")
test_text = "> INTERNAL ONLY — Draft for Ray review.\n> Do not publish.\n\n# Content\n"
with_all = add_cta_section(test_text, "newsletter")
# The marker line should remain intact
check("first line intact after CTA insert", with_all.startswith("> INTERNAL ONLY"))
check("CTA not embedded in marker line",
      "\n> INTERNAL ONLY" not in with_all.replace("> INTERNAL ONLY — Draft", ""))

# ── Long file: CTA inserted within scorer window ─────────────────────────────
print("\n-- long file: CTA visible within scorer window --")
long_text = BASE + ("X" * (_SCORER_READ_LIMIT * 2)) + "\njoin the program here\n"
# Full text has "join" past char 3000 — old guard would miss the insert
fixed_long = add_cta_section(long_text, "youtube_script")
window_long = fixed_long[:_SCORER_READ_LIMIT]
check("CTA present in window of long file", detect_missing_cta(window_long) is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
