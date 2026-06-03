"""
test_cfo_brain_option_selection.py
Phase 7B: CFO Brain — option selection handler.
Verifies "LET'S DO 1" and "OPTION 2" style messages.
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


from lib.hermes_cfo_brain import classify_cfo_intent, handle_option_selection

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "artifact_inventory",
    "HERMES REPORT",
]

print("\nCFO Brain Option Selection Tests")
print("=" * 50)

print("\n-- Intent classification --")
_OPTION_MSGS = [
    "let's do 1",
    "lets do 1",
    "do option 2",
    "option 1",
    "option 2",
    "go with option 3",
    "do 1",
    "pick 2",
    "i choose option 1",
    "we'll go with 2",
    "let's go with 3",
]
for msg in _OPTION_MSGS:
    check(f"'{msg}' → option_selection",
          classify_cfo_intent(msg.lower()) == "option_selection")

print("\n-- Response format: no prior context --")
resp = handle_option_selection("let's do 1", {})
check("response not None", resp is not None)
check("has OPTION SELECTED header", resp.startswith("OPTION SELECTED"))
check("approval boundary present", "explicit ray approval" in resp.lower())
for marker in EVIDENCE_DUMP_MARKERS:
    check(f"no evidence dump marker: {marker!r}", marker not in resp)

print("\n-- Number-only message '1' → option_selection --")
check("'1' → option_selection", classify_cfo_intent("1") == "option_selection")
check("'2' → option_selection", classify_cfo_intent("2") == "option_selection")

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
