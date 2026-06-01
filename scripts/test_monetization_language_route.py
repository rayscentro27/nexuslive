"""test_monetization_language_route.py — Monetization questions route to opportunities."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_monetization_language_route ===\n")
from lib.hermes_conversational_router import classify_conversational_intent, route_conversational_intent
from lib.hermes_language_pack import CATEGORY_MONETIZATION
phrases = [
    "what is the best money making opportunity right now",
    "what can make money right now", "best revenue move",
    "how do we make money today", "best money making",
    "what makes money", "revenue opportunity",
]
for phrase in phrases:
    cat = classify_conversational_intent(phrase)
    check(f"'{phrase}' → monetization", cat == CATEGORY_MONETIZATION)
    resp = route_conversational_intent(phrase)
    check(f"'{phrase}' returns response", isinstance(resp, str) and len(resp) > 5)
    check(f"'{phrase}' no stale exec memory", "Hermes Executive Memory (v1" not in (resp or ""))
    check(f"'{phrase}' no OFFLINE", "OFFLINE" not in (resp or ""))
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
