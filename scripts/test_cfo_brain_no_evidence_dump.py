"""
test_cfo_brain_no_evidence_dump.py
Phase 7B: CFO Brain — no evidence dump.
Verifies that all 7 live Telegram failure scenarios produce
correct headers and no evidence dumps.
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


from lib.hermes_cfo_brain import (
    handle_simplify_request, handle_explain_request, handle_option_selection,
    handle_task_reference, handle_morning_activity, handle_queue_status,
    handle_failure_feedback, classify_cfo_intent, should_use_cfo_brain,
)

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "Source 2:",
    "artifact_inventory",
    "handoff_state",
    "HERMES REPORT",
]

GENERIC_FALLBACK_MARKERS = [
    "based on what i have available",
    "i wasn't fully sure",
    "based on available information",
]

def assert_no_evidence_dump(label, response):
    for marker in EVIDENCE_DUMP_MARKERS:
        check(f"{label} — no marker: {marker!r}", marker not in (response or ""))

def assert_no_generic_fallback(label, response):
    for marker in GENERIC_FALLBACK_MARKERS:
        check(f"{label} — no generic fallback: {marker!r}",
              marker not in (response or "").lower())

print("\nCFO Brain No Evidence Dump Tests (7 Live Scenarios)")
print("=" * 60)

# Scenario 1: CAN YOU SIMPLIFY YOUR RESPONSE
print("\n-- Scenario 1: CAN YOU SIMPLIFY YOUR RESPONSE --")
r1 = handle_simplify_request("can you simplify your response", {})
check("response not None", r1 is not None)
assert_no_evidence_dump("simplify", r1)
assert_no_generic_fallback("simplify", r1)
check("approval boundary", "explicit ray approval" in (r1 or "").lower())

# Scenario 2: WHAT WAS TASK 1
print("\n-- Scenario 2: WHAT WAS TASK 1 --")
r2 = handle_task_reference("what was task 1", {})
check("response not None", r2 is not None)
check("has PLAIN ANSWER header", "PLAIN ANSWER" in (r2 or ""))
assert_no_evidence_dump("task reference", r2)
assert_no_generic_fallback("task reference", r2)

# Scenario 3: WHAT DID YOU DO THIS MORNING
print("\n-- Scenario 3: WHAT DID YOU DO THIS MORNING --")
r3 = handle_morning_activity("what did you do this morning", {})
check("response not None", r3 is not None)
check("has MORNING SUMMARY header", "MORNING SUMMARY" in (r3 or ""))
assert_no_evidence_dump("morning activity", r3)
assert_no_generic_fallback("morning activity", r3)

# Scenario 4: WHAT TASK ARE IN THE QUEUE
print("\n-- Scenario 4: WHAT TASK ARE IN THE QUEUE --")
r4 = handle_queue_status("what task are in the queue", {})
check("response not None", r4 is not None)
check("has TASK QUEUE header", "TASK QUEUE" in (r4 or ""))
assert_no_evidence_dump("queue status", r4)
assert_no_generic_fallback("queue status", r4)

# Scenario 5: LET'S DO 1
print("\n-- Scenario 5: LET'S DO 1 --")
r5 = handle_option_selection("let's do 1", {})
check("response not None", r5 is not None)
check("has OPTION SELECTED header", "OPTION SELECTED" in (r5 or ""))
assert_no_evidence_dump("option selection", r5)
assert_no_generic_fallback("option selection", r5)

# Scenario 6: AND WHAT DOES THAT MEAN
print("\n-- Scenario 6: AND WHAT DOES THAT MEAN --")
r6 = handle_explain_request("and what does that mean", {})
check("response not None", r6 is not None)
assert_no_evidence_dump("explain request", r6)
assert_no_generic_fallback("explain request", r6)

# Scenario 7: EXPLAIN YOUR RECOMMENDATION IN PLAIN LANGUAGE
print("\n-- Scenario 7: EXPLAIN YOUR RECOMMENDATION IN PLAIN LANGUAGE --")
r7 = handle_explain_request("explain your recommendation in plain language", {})
check("response not None", r7 is not None)
assert_no_evidence_dump("explain recommendation", r7)
assert_no_generic_fallback("explain recommendation", r7)

# Failure feedback scenario
print("\n-- Scenario 8: THAT IS NOT WHAT I MEANT --")
r8 = handle_failure_feedback("that is not what i meant", {})
check("response not None", r8 is not None)
check("has CORRECTING COURSE header", "CORRECTING COURSE" in (r8 or ""))
assert_no_evidence_dump("failure feedback", r8)

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
