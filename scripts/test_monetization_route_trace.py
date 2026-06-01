"""
test_monetization_route_trace.py
Traces the exact routing path for each monetization phrase to confirm
each one reaches the content-first handler, not the old evidence dump.

Also verifies that raw evidence/debug commands are NOT blocked.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_monetization_route_trace ===\n")

from hermes_command_router.intake import classify_intent
from lib.hermes_conversational_router import classify_conversational_intent
from lib.hermes_language_pack import CATEGORY_MONETIZATION
from hermes_command_router.router import run_command

# ── Trace 1: intake classify_intent ──────────────────────────────────────────
print("-- intake.py classify_intent --")
audit_phrases = [
    "nexus monetization audit",
    "run nexus monetization audit",
    "show monetization audit",
    "monetization audit",
    "monetization plan",
    "monetization priorities",
    "revenue plan for today",
    "fastest money path",
    "how do we make money today",
    "how to make money today",
    "best money making opportunity",
]
for phrase in audit_phrases:
    intent, _, _ = classify_intent(phrase)
    check(f"intake '{phrase[:40]}' → business_opportunities", intent == "business_opportunities")

# ── Trace 2: conversational router classifies monetization phrases ─────────────
print("\n-- conversational_router classify_conversational_intent --")
convo_phrases = [
    "how do we make money today",
    "how to make money today",
    "best money making opportunity",
    "what can make money this week",
    "best revenue move",
    "nexus monetization audit",
    "monetization priorities",
]
for phrase in convo_phrases:
    intent = classify_conversational_intent(phrase)
    check(f"convo '{phrase[:40]}' → {CATEGORY_MONETIZATION}", intent == CATEGORY_MONETIZATION)

# ── Trace 3: end-to-end run_command produces content-first response ────────────
print("\n-- run_command end-to-end traces --")

phrases_to_check = [
    "how do we make money today",
    "nexus monetization audit",
    "monetization priorities",
]
# Content-first markers: at least one of these must appear in the response
CONTENT_FIRST_MARKERS = [
    "Lead Magnet", "Newsletter", "Short Video Script", "Simplified",
    "Cleaned", "asset", "score", "HEALTHY", "approval",
    "TODAY'S MONEY PLAN", "NEXUS MONETIZATION AUDIT",
]
FORBIDDEN = [
    "I can answer from verified artifacts",
    "Monetization evidence:",
    "[artifact_inventory]",
]
for phrase in phrases_to_check:
    result = run_command(phrase)
    has_content = any(m in result for m in CONTENT_FIRST_MARKERS)
    check(f"'{phrase[:35]}' has content-first info", has_content)
    for f in FORBIDDEN:
        check(f"'{phrase[:35]}' no '{f[:30]}'", f not in result)

# ── Trace 4: raw evidence commands still work ─────────────────────────────────
print("\n-- Raw evidence/debug commands NOT blocked --")
raw_evidence_phrases = [
    "show evidence",
    "what artifacts do you have",
    "evidence only",
    "what evidence do you have",
]
for phrase in raw_evidence_phrases:
    intent, _, _ = classify_intent(phrase)
    result = run_command(phrase)
    check(f"'{phrase}' still returns a response", bool(result))
    # These should NOT produce monetization audit headers
    check(f"'{phrase}' not hijacked to monetization audit",
          "NEXUS MONETIZATION AUDIT" not in result)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
