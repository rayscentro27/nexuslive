"""
test_cfo_brain_plain_language_explanation.py
Phase 7B: CFO Brain — plain language explanation handler.
Verifies "EXPLAIN YOUR RECOMMENDATION IN PLAIN LANGUAGE" and
"AND WHAT DOES THAT MEAN" style messages.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passes = 0
failures = 0

def check(label, cond):
    global passes, failures
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures += 1
    else:
        passes += 1
    print(f"  [{status}] {label}")
    return cond


from lib.hermes_cfo_brain import classify_cfo_intent, handle_explain_request
from lib.hermes_plain_language_rewriter import (
    explain_response_plainly, remove_jargon, format_plain_answer
)

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "artifact_inventory",
    "HERMES REPORT",
]

print("\nCFO Brain Plain Language Explanation Tests")
print("=" * 50)

print("\n-- Intent classification --")
_EXPLAIN_MSGS = [
    "and what does that mean",
    "what does that mean",
    "explain your recommendation",
    "explain in plain language",
    "explain your recommendation in plain language",
    "in plain language",
    "plain language explanation",
    "what do you mean",
    "explain that",
    "what did you mean by",
]
for msg in _EXPLAIN_MSGS:
    check(f"'{msg}' → explain_previous_response",
          classify_cfo_intent(msg.lower()) == "explain_previous_response")

print("\n-- Response format: no prior context --")
resp = handle_explain_request("explain your recommendation in plain language", {})
check("response not None", resp is not None)
check("approval boundary present", "explicit ray approval" in resp.lower())
for marker in EVIDENCE_DUMP_MARKERS:
    check(f"no evidence dump marker: {marker!r}", marker not in resp)

print("\n-- remove_jargon strips technical terms --")
JARGON_TEXT = "The intent classifier used a deterministic handler to process confidence score."
cleaned = remove_jargon(JARGON_TEXT)
check("remove_jargon returns string", isinstance(cleaned, str))
check("'intent classifier' replaced", "intent classifier" not in cleaned)
check("'deterministic handler' replaced", "deterministic handler" not in cleaned)

print("\n-- format_plain_answer produces standard format --")
pa = format_plain_answer(
    answer="Revenue readiness is 72/100.",
    why="You have the assets but no funnel yet.",
    recommendation="Activate the lead magnet this week.",
    next_step="Say 'let's do 1' to proceed.",
    approval_boundary="I will not publish without Ray approval.",
)
check("format_plain_answer returns string", isinstance(pa, str))
check("contains answer", "72/100" in pa)
check("contains recommendation", "lead magnet" in pa.lower())

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
