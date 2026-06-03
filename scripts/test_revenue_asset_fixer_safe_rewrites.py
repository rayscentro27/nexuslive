"""
test_revenue_asset_fixer_safe_rewrites.py
Tests: fix_asset_text applies all needed fixes and the fixed text passes re-detection.
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


print("=== test_revenue_asset_fixer_safe_rewrites ===\n")

from lib.hermes_revenue_asset_fixer import (
    fix_asset_text,
    detect_missing_internal_marker,
    detect_missing_cta,
    detect_missing_compliance_note,
    detect_missing_revenue_connection,
    detect_unsafe_promise_language,
    _SCORER_READ_LIMIT,
)

BARE_TEXT = "# Business Readiness Guide\n\nThis article explains how lenders evaluate applications.\n"

# ── fix_asset_text returns tuple ──────────────────────────────────────────────
print("-- fix_asset_text returns (text, applied_list) --")
result = fix_asset_text(BARE_TEXT, "lead_magnet")
check("returns tuple of length 2", isinstance(result, tuple) and len(result) == 2)
fixed_text, applied = result
check("fixed_text is str", isinstance(fixed_text, str))
check("applied is list", isinstance(applied, list))
check("at least one fix applied", len(applied) >= 1)

# ── All fixes detected as missing on bare text ───────────────────────────────
print("\n-- all fixes detected as missing on bare text --")
check("internal marker missing in bare",   detect_missing_internal_marker(BARE_TEXT) is True)
check("cta missing in bare",               detect_missing_cta(BARE_TEXT) is True)
check("compliance missing in bare",        detect_missing_compliance_note(BARE_TEXT) is True)
check("revenue connection missing in bare", detect_missing_revenue_connection(BARE_TEXT) is True)

# ── Fixed text passes detection within scorer read limit ─────────────────────
print("\n-- fixed text passes detection within scorer window --")
window = fixed_text[:_SCORER_READ_LIMIT]
check("no missing internal marker in fixed",   detect_missing_internal_marker(fixed_text) is False)
check("no missing cta in fixed window",        detect_missing_cta(window) is False)
check("no missing compliance in fixed window", detect_missing_compliance_note(window) is False)
check("no missing revenue conn in fixed window", detect_missing_revenue_connection(window) is False)

# ── Unsafe promise text gets fixed ───────────────────────────────────────────
print("\n-- unsafe promise removal --")
unsafe_text = "# Guide\n\nWe guarantee you get approved for funding.\n"
fixed_unsafe, applied_unsafe = fix_asset_text(unsafe_text, "seo_article")
check("unsafe_promise_language_softened in applied", any("unsafe" in a for a in applied_unsafe))
check("no 'guarantee' in fixed", "guarantee" not in fixed_unsafe.lower()
      or "does not guarantee" in fixed_unsafe.lower()
      or "help identify gaps in" in fixed_unsafe.lower())

# ── Already-fixed text doesn't get double-fixed ──────────────────────────────
print("\n-- idempotency: second fix has nothing to apply --")
fixed2, applied2 = fix_asset_text(fixed_text, "lead_magnet")
check("second pass applies nothing new", len(applied2) == 0)
check("text unchanged on second pass", fixed2 == fixed_text)

# ── Asset type CTA is type-appropriate ───────────────────────────────────────
print("\n-- CTA contains scorer-recognizable pattern --")
from lib.hermes_revenue_asset_fixer import _CTA_BY_TYPE, _CTA_DEFAULT
CTA_PATTERNS = ["start your", "download", "sign up", "get your", "check your", "fix your", "join"]
for atype, cta in _CTA_BY_TYPE.items():
    cta_lower = cta.lower()
    has_pattern = any(p in cta_lower for p in CTA_PATTERNS)
    check(f"CTA for '{atype}' has scorer pattern", has_pattern)
default_lower = _CTA_DEFAULT.lower()
check("_CTA_DEFAULT has scorer pattern", any(p in default_lower for p in CTA_PATTERNS))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
