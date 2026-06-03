"""
test_cfo_brain_unknown_to_scout.py
Phase 7B: CFO Brain — unknown answer → scout dispatch.
Verifies unknown questions are dispatched, not guessed.
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


from lib.hermes_cfo_brain import classify_cfo_intent, handle_unknown_with_scout_dispatch

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "artifact_inventory",
    "HERMES REPORT",
]

GENERIC_FALLBACK_MARKERS = [
    "based on what i have available",
    "i wasn't fully sure",
    "you may want to check",
]

print("\nCFO Brain Unknown → Scout Dispatch Tests")
print("=" * 50)

print("\n-- Scout dispatch intent classification --")
_SCOUT_MSGS = [
    ("can your scouts figure it out", "scout_dispatch_request"),
    ("can hermes research this", "scout_dispatch_request"),
    ("research this for me", "scout_dispatch_request"),
    ("find out for me", "scout_dispatch_request"),
    ("look into this", "scout_dispatch_request"),
]
for msg, expected in _SCOUT_MSGS:
    check(f"'{msg}' → {expected}", classify_cfo_intent(msg.lower()) == expected)

print("\n-- Unknown dispatch response format --")
resp = handle_unknown_with_scout_dispatch("can your scouts research this?", {})
check("response not None", resp is not None)
check("approval boundary present", "explicit ray approval" in (resp or "").lower())
for marker in EVIDENCE_DUMP_MARKERS:
    check(f"no evidence dump: {marker!r}", marker not in (resp or ""))
for marker in GENERIC_FALLBACK_MARKERS:
    check(f"no generic fallback: {marker!r}", marker not in (resp or "").lower())

print("\n-- CFO doctrine: unknown answer rules loaded --")
try:
    from lib.hermes_cfo_doctrine import get_unknown_answer_rules
    rules = get_unknown_answer_rules()
    check("unknown answer rules loaded", len(rules) > 10)
    check("dispatch rule present", "dispatch" in rules.lower() or "scout" in rules.lower())
    check("never guess rule present", "never guess" in rules.lower() or "do not guess" in rules.lower() or "never" in rules.lower())
except Exception as e:
    check(f"doctrine loads: {e}", False)

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
