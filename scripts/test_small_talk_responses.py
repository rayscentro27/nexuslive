"""test_small_talk_responses.py — Small talk must return natural response, not evidence dump."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_small_talk_responses ===\n")
from lib.hermes_conversational_router import route_conversational_intent, classify_conversational_intent
from lib.hermes_language_pack import CATEGORY_SMALL_TALK
BAD = ["artifact_inventory", "OFFLINE", "Beehiiv", "strategic context", "executive memory"]
phrases = [
    "did you get sleep last night", "did you sleep", "how are you",
    "are you awake", "are you online", "good morning", "good afternoon",
    "good evening", "how are you doing",
]
for phrase in phrases:
    cat = classify_conversational_intent(phrase)
    check(f"'{phrase}' → small_talk", cat == CATEGORY_SMALL_TALK)
    resp = route_conversational_intent(phrase)
    check(f"'{phrase}' returns response", isinstance(resp, str) and len(resp) > 5)
    for bad in BAD:
        check(f"'{phrase}' no '{bad}'", bad.lower() not in (resp or "").lower())
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
