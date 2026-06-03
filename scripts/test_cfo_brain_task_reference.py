"""
test_cfo_brain_task_reference.py
Phase 7B: CFO Brain — task reference handler.
Verifies "WHAT WAS TASK 1" style messages.
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


from lib.hermes_cfo_brain import classify_cfo_intent, handle_task_reference

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "artifact_inventory",
    "HERMES REPORT",
]

print("\nCFO Brain Task Reference Tests")
print("=" * 50)

print("\n-- Intent classification --")
_TASK_MSGS = [
    "what was task 1",
    "task 1",
    "task 2",
    "what is task 3",
    "first task",
    "second task",
    "what were the tasks",
    "show me task 1",
    "what was the first",
]
for msg in _TASK_MSGS:
    check(f"'{msg}' → task_reference",
          classify_cfo_intent(msg.lower()) == "task_reference")

print("\n-- Response format: no prior context --")
resp = handle_task_reference("what was task 1", {})
check("response not None", resp is not None)
check("has PLAIN ANSWER header", "PLAIN ANSWER" in resp)
check("approval boundary present", "explicit ray approval" in resp.lower())
for marker in EVIDENCE_DUMP_MARKERS:
    check(f"no evidence dump marker: {marker!r}", marker not in resp)

print("\n-- Response mentions task number when context missing --")
check("mentions 'task 1'", "task 1" in resp.lower() or "Task 1" in resp)

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
