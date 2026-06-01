"""
test_monetization_question_recommendation.py
Verifies the monetization question returns a content-first recommendation,
not just "run nexus monetization audit".
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes_command_router.router import run_command, _run_business_opportunities
from hermes_command_router.intake import classify_intent
from lib.hermes_conversational_router import classify_conversational_intent
from lib.hermes_language_pack import CATEGORY_MONETIZATION

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_monetization_question_recommendation ===\n")

# 1. Intent classification for monetization phrases
print("-- Intent classification --")
for phrase in [
    "how do we make money today",
    "what can make money right now",
    "best money making opportunity",
    "how to make money today",
    "best revenue move",
]:
    intent = classify_conversational_intent(phrase)
    check(f"'{phrase}' -> {CATEGORY_MONETIZATION}", intent == CATEGORY_MONETIZATION)

# 2. _run_business_opportunities returns status + evidence
print("\n-- Handler output --")
status, evidence, rec = _run_business_opportunities()
full_evidence = "\n".join(evidence)
full_text = full_evidence + "\n" + rec

check("status is healthy or unknown (not None)", status in ("healthy", "unknown"))
check("evidence is non-empty list", len(evidence) > 0)
check("recommendation is non-empty string", bool(rec))

# 3. Response does NOT just say "Run nexus monetization audit" with nothing else
weak_only = rec.strip().lower() == "run nexus monetization audit"
check("not just 'run nexus monetization audit'", not weak_only)

# 4. If healthy, response includes approval boundary note
if status == "healthy":
    check("includes approval boundary", "approval" in full_text.lower())
    check("includes 'nexus monetization audit' as secondary suggestion",
          "nexus monetization audit" in full_text.lower())

# 5. run_command round-trip
print("\n-- run_command round-trip --")
result = run_command("how do we make money today")
check("run_command returns non-empty string", bool(result))
check("result does not say only 'run nexus monetization audit'",
      "Run nexus monetization audit" not in result or len(result) > 60)
check("result has no raw evidence dump", "ARCHIVED EXECUTIVE MEMORY" not in result)
check("result has no stale provider claims", "OFFLINE" not in result)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
