"""
test_cfo_brain_live_scenarios.py
Phase 7B: CFO Brain — live scenario validation.
Verifies all 7 live Telegram failures from the Phase 7B directive
are handled correctly by the routing stack.
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
    should_use_cfo_brain, classify_cfo_intent, process_with_cfo_brain,
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

def no_evidence_dump(resp):
    return all(m not in (resp or "") for m in EVIDENCE_DUMP_MARKERS)

def no_generic_fallback(resp):
    return all(m not in (resp or "").lower() for m in GENERIC_FALLBACK_MARKERS)

print("\nCFO Brain Live Scenario Validation")
print("=" * 60)

print("\n-- Scenario 1: CAN YOU SIMPLIFY YOUR RESPONSE --")
msg = "CAN YOU SIMPLIFY YOUR RESPONSE"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = simplify_previous_response",
      classify_cfo_intent(msg.lower()) == "simplify_previous_response")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("no evidence dump", no_evidence_dump(r))
check("no generic fallback", no_generic_fallback(r))
check("approval boundary", "explicit ray approval" in (r or "").lower())

print("\n-- Scenario 2: WHAT WAS TASK 1 --")
msg = "WHAT WAS TASK 1"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = task_reference",
      classify_cfo_intent(msg.lower()) == "task_reference")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("has PLAIN ANSWER header", "PLAIN ANSWER" in (r or ""))
check("no evidence dump", no_evidence_dump(r))
check("no generic fallback", no_generic_fallback(r))

print("\n-- Scenario 3: WHAT DID YOU DO THIS MORNING --")
msg = "WHAT DID YOU DO THIS MORNING"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = morning_activity_question",
      classify_cfo_intent(msg.lower()) == "morning_activity_question")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("has MORNING SUMMARY header", "MORNING SUMMARY" in (r or ""))
check("no evidence dump", no_evidence_dump(r))

print("\n-- Scenario 4: WHAT TASK ARE IN THE QUEUE --")
msg = "WHAT TASK ARE IN THE QUEUE"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = queue_status_question",
      classify_cfo_intent(msg.lower()) == "queue_status_question")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("has TASK QUEUE header", "TASK QUEUE" in (r or ""))
check("no evidence dump", no_evidence_dump(r))

print("\n-- Scenario 5: LET'S DO 1 --")
msg = "LET'S DO 1"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = option_selection",
      classify_cfo_intent(msg.lower()) == "option_selection")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("has OPTION SELECTED header", "OPTION SELECTED" in (r or ""))
check("no evidence dump", no_evidence_dump(r))

print("\n-- Scenario 6: AND WHAT DOES THAT MEAN --")
msg = "AND WHAT DOES THAT MEAN"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = explain_previous_response",
      classify_cfo_intent(msg.lower()) == "explain_previous_response")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("no evidence dump", no_evidence_dump(r))
check("no generic fallback", no_generic_fallback(r))

print("\n-- Scenario 7: EXPLAIN YOUR RECOMMENDATION IN PLAIN LANGUAGE --")
msg = "EXPLAIN YOUR RECOMMENDATION IN PLAIN LANGUAGE"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = explain_previous_response",
      classify_cfo_intent(msg.lower()) == "explain_previous_response")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("no evidence dump", no_evidence_dump(r))
check("no generic fallback", no_generic_fallback(r))

print("\n-- Bonus: HOW DO WE MAKE MONEY THIS WEEK --")
msg = "HOW DO WE MAKE MONEY THIS WEEK"
check("brain activates", should_use_cfo_brain(msg.lower()) is True)
check("intent = money_strategy_question",
      classify_cfo_intent(msg.lower()) == "money_strategy_question")
r = process_with_cfo_brain(msg)
check("response not None", r is not None)
check("has WEEKLY MONEY PLAN header", "WEEKLY MONEY PLAN" in (r or ""))
check("no evidence dump", no_evidence_dump(r))

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
