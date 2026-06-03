"""
test_revenue_asset_fixer_unsafe_promise_removal.py
Tests: remove_unsafe_promise_language replaces guarantee/approval language correctly.
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


print("=== test_revenue_asset_fixer_unsafe_promise_removal ===\n")

from lib.hermes_revenue_asset_fixer import (
    remove_unsafe_promise_language,
    detect_unsafe_promise_language,
)

# ── Each unsafe pattern is replaced ──────────────────────────────────────────
print("-- unsafe patterns replaced --")

cases = [
    ("We guarantee results.",               "guarantee",         True),
    ("Guaranteed funding approval.",         "guaranteed funding", True),
    ("100% approval rate.",                  "100% approval",     True),
    ("Guaranteed approval program here.",    "guaranteed approval", True),
    ("This content guarantees success.",     "guarantees",        True),
]

for text, label, expect_changed in cases:
    fixed = remove_unsafe_promise_language(text)
    remaining = detect_unsafe_promise_language(fixed)
    check(f"'{label}' → no more unsafe in fixed", len(remaining) == 0)
    if expect_changed:
        check(f"'{label}' → text was changed", fixed != text)

# ── Specific replacement values ───────────────────────────────────────────────
print("\n-- specific replacement values --")

g = remove_unsafe_promise_language("We guarantee you results.")
check("'guarantee' → safer language",
      "help identify gaps in" in g.lower() or "cannot ensure" in g.lower()
      or "support" in g.lower() or "help" in g.lower())

gd = remove_unsafe_promise_language("Guaranteed approval for all.")
check("'guaranteed approval' → 'improved approval readiness'",
      "improved approval readiness" in gd.lower() or "approval readiness" in gd.lower())

# ── Clean text is returned unchanged ─────────────────────────────────────────
print("\n-- clean text unchanged --")
clean = "Learn how lenders evaluate funding applications."
check("clean text unchanged", remove_unsafe_promise_language(clean) == clean)

# ── Multiple instances in one text ───────────────────────────────────────────
print("\n-- multiple instances --")
multi = "We guarantee approval. Guaranteed results. You will get approved."
fixed_multi = remove_unsafe_promise_language(multi)
remaining_multi = detect_unsafe_promise_language(fixed_multi)
check("all instances removed from multi-instance text", len(remaining_multi) == 0)

# ── Does not guarantee (compliance) is handled ───────────────────────────────
print("\n-- 'does not guarantee' compliance language --")
compliance_text = "This content does not guarantee funding approval."
fixed_compliance = remove_unsafe_promise_language(compliance_text)
check("'does not guarantee' → safer language (no 'guarantee' remaining)",
      len(detect_unsafe_promise_language(fixed_compliance)) == 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
