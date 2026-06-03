"""
test_revenue_packet_improved_cta_set.py
Tests: build_improved_cta_set returns 8-category dict;
       each category is a non-empty string;
       no payment/affiliate language.
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


print("=== test_revenue_packet_improved_cta_set ===\n")

from lib.hermes_revenue_asset_packet import build_improved_cta_set, IMPROVED_CTA_SET

# ── 8-category completeness ───────────────────────────────────────────────────
print("-- 8-category completeness --")
EXPECTED_CATEGORIES = {
    "lead_magnet", "newsletter", "short_video", "landing_page",
    "direct_offer", "soft_educational", "consultation", "nexus_membership",
}
cta_set = build_improved_cta_set()
check("returns dict", isinstance(cta_set, dict))
check("has 8 categories", len(cta_set) == 8)
for cat in EXPECTED_CATEGORIES:
    check(f"'{cat}' present", cat in cta_set)

# ── Each CTA is a non-empty string ────────────────────────────────────────────
print("\n-- each CTA is non-empty string --")
for cat, text in cta_set.items():
    check(f"[{cat}] is non-empty string", isinstance(text, str) and len(text) > 0)

# ── No unsafe language ────────────────────────────────────────────────────────
print("\n-- no unsafe language in CTAs --")
UNSAFE_PATTERNS = [
    "guarantee", "100% success", "i promise", "we promise",
    "no risk", "risk-free guarantee",
]
for cat, text in cta_set.items():
    text_lower = text.lower()
    for pattern in UNSAFE_PATTERNS:
        check(f"[{cat}] no '{pattern}'", pattern not in text_lower)

# ── IMPROVED_CTA_SET constant matches build_improved_cta_set() ───────────────
print("\n-- IMPROVED_CTA_SET constant --")
check("IMPROVED_CTA_SET is dict", isinstance(IMPROVED_CTA_SET, dict))
check("IMPROVED_CTA_SET has 8 entries", len(IMPROVED_CTA_SET) == 8)
check("build_improved_cta_set() == IMPROVED_CTA_SET", build_improved_cta_set() == IMPROVED_CTA_SET)

# ── CTAs reference funding/credit/Nexus ──────────────────────────────────────
print("\n-- CTAs reference funding/credit/Nexus --")
full_text = " ".join(cta_set.values()).lower()
check("funding mentioned in CTAs", "funding" in full_text)
check("readiness or ready mentioned in CTAs", "readiness" in full_text or "ready" in full_text)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
