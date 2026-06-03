"""
test_cfo_brain_simplify_response.py
Phase 7B: CFO Brain — simplify response handler.
Verifies "CAN YOU SIMPLIFY YOUR RESPONSE" style messages.
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


from lib.hermes_cfo_brain import classify_cfo_intent, handle_simplify_request
from lib.hermes_plain_language_rewriter import simplify_response_text

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "artifact_inventory",
    "HERMES REPORT",
]

print("\nCFO Brain Simplify Response Tests")
print("=" * 50)

print("\n-- Intent classification --")
_SIMPLIFY_MSGS = [
    "can you simplify your response",
    "simplify your response",
    "simplify that",
    "make it simpler",
    "shorter version",
    "can you simplify",
    "in short",
    "brief version",
    "summarize that",
    "simplify the response",
]
for msg in _SIMPLIFY_MSGS:
    check(f"'{msg}' → simplify_previous_response",
          classify_cfo_intent(msg.lower()) == "simplify_previous_response")

print("\n-- Response format: no prior context --")
resp = handle_simplify_request("can you simplify your response", {})
check("response not None", resp is not None)
check("approval boundary present", "explicit ray approval" in resp.lower())
for marker in EVIDENCE_DUMP_MARKERS:
    check(f"no evidence dump marker: {marker!r}", marker not in resp)

print("\n-- simplify_response_text strips evidence dumps --")
BAD_RESPONSE = """HERMES REPORT
════════════════════════

artifact_inventory:
  - revenue_asset_packet.json (score: 72)

Live answer sources:
  - Executive Memory v2: accessed

Confidence: MEDIUM

Revenue readiness: 72/100
Top action: activate the lead magnet funnel
"""
simplified = simplify_response_text(BAD_RESPONSE, max_bullets=5)
check("simplified is not None", simplified is not None)
check("artifact_inventory stripped", "artifact_inventory" not in simplified)
check("Live answer sources stripped", "Live answer sources:" not in simplified)
check("Confidence stripped", "Confidence: " not in simplified)

print("\n-- simplify_response_text handles plain text --")
PLAIN = "Revenue readiness: 72/100.\nTop action: activate the lead magnet.\nMy recommendation: do it now."
simplified2 = simplify_response_text(PLAIN, max_bullets=3)
check("plain text simplified", simplified2 is not None)
check("simplified is a string", isinstance(simplified2, str))

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
