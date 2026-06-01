"""test_system_health_language_route.py — System health questions route to health handler."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_system_health_language_route ===\n")
from lib.hermes_conversational_router import classify_conversational_intent, route_conversational_intent
from lib.hermes_language_pack import CATEGORY_SYSTEM_HEALTH
phrases = [
    "what is the system health", "what is system health",
    "is nexus healthy", "what is broken", "what is down",
    "are the systems running", "system health",
]
for phrase in phrases:
    cat = classify_conversational_intent(phrase)
    check(f"'{phrase}' → system_health", cat == CATEGORY_SYSTEM_HEALTH)
    resp = route_conversational_intent(phrase)
    check(f"'{phrase}' returns response", isinstance(resp, str) and len(resp) > 5)
    check(f"'{phrase}' no stale exec memory", "Hermes Executive Memory (v1" not in (resp or ""))
    check(f"'{phrase}' no artifact_inventory", "artifact_inventory" not in (resp or "").lower())
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
