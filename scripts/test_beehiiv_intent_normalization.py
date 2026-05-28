"""
test_beehiiv_intent_normalization.py
======================================
Verify all Beehiiv/Beehive aliases route to premium_blocker_resolver,
NOT to funding/loan/research content.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hermes_command_router.intake import classify_intent
from lib.hermes_evidence_mode import is_beehiiv_query

PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_beehiiv_intent_normalization ===\n")

BEEHIIV_VARIANTS = [
    "what's a free alternative to beehiiv",
    "I want to replace beehiiv with something free",
    "beehive newsletter platform alternatives",
    "bee hive is too expensive, what else",
    "bee-hive free tier options",
    "behive newsletter platform",
    "behiiv alternative",
    "newsletter platform alternatives",
    "email platform alternative for newsletters",
    "newsletter tool alternative",
    "premium blocker for newsletter tool",
    "cheap alternative to email marketing tool",
]

for phrase in BEEHIIV_VARIANTS:
    intent, priority, _ = classify_intent(phrase)
    check(
        f"'{phrase[:55]}' → premium_blocker_resolver (got: {intent})",
        intent == "premium_blocker_resolver"
    )

# These should NOT route to premium_blocker_resolver
NON_BEEHIIV = [
    "what is the latest credit repair strategy",
    "show me funding opportunities",
    "what did nexus produce this week",
    "grant research for small business",
]

for phrase in NON_BEEHIIV:
    intent, _, _ = classify_intent(phrase)
    check(
        f"'{phrase[:55]}' does NOT route to premium_blocker_resolver (got: {intent})",
        intent != "premium_blocker_resolver"
    )

# Test evidence mode normalization function
print("\n  Evidence mode is_beehiiv_query():")
for alias in ["beehiiv", "beehive", "bee hive", "bee-hive", "behive", "behiiv",
              "newsletter alternative", "email platform alternative"]:
    result = is_beehiiv_query(alias)
    check(f"is_beehiiv_query('{alias}') is True", result)

check("is_beehiiv_query('funding grant') is False",
      not is_beehiiv_query("funding grant"))

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
