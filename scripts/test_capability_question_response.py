"""test_capability_question_response.py — Capability questions get the capability list."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_capability_question_response ===\n")
from lib.hermes_conversational_router import route_conversational_intent, classify_conversational_intent
from lib.hermes_language_pack import CATEGORY_CAPABILITY
phrases = ["what can you answer", "what can you do", "help", "what can i ask you",
           "what are your capabilities", "what do you support"]
for phrase in phrases:
    cat = classify_conversational_intent(phrase)
    check(f"'{phrase}' → capability", cat == CATEGORY_CAPABILITY)
    resp = route_conversational_intent(phrase)
    check(f"'{phrase}' returns capability response", isinstance(resp, str))
    check(f"'{phrase}' has bullets", "•" in (resp or ""))
    check(f"'{phrase}' no evidence dump", "artifact_inventory" not in (resp or "").lower())
    check(f"'{phrase}' no OFFLINE", "OFFLINE" not in (resp or ""))
    check(f"'{phrase}' mentions knowledge gaps", "gap" in (resp or "").lower())
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
