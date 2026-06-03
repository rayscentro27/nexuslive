"""
test_cfo_brain_failure_learning.py
Phase 7B: CFO Brain — failure learning module.
Verifies log_failed_response, classify_failure_type, generate_test_from_failure.
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


from lib.hermes_failure_learning import (
    classify_failure_type, generate_test_from_failure,
    log_failed_response, format_failure_review, FAILURE_TYPES,
)

print("\nCFO Brain Failure Learning Tests")
print("=" * 50)

print("\n-- Failure type constants --")
_REQUIRED_TYPES = [
    "evidence_dump", "generic_quality_fallback", "wrong_tool",
    "lost_context", "failed_followup", "too_technical",
    "did_not_assign_scout", "did_not_create_prompt",
    "unsafe_action_attempt", "duplicate_queue_item",
]
for ft in _REQUIRED_TYPES:
    check(f"failure type '{ft}' defined", ft in FAILURE_TYPES)

print("\n-- classify_failure_type: evidence dump --")
EVIDENCE_DUMP_RESPONSE = (
    "HERMES REPORT\nartifact_inventory:\n  - revenue_asset.json\n"
    "Live answer sources:\n  - Executive Memory v2\nConfidence: MEDIUM"
)
ft = classify_failure_type("can you simplify", EVIDENCE_DUMP_RESPONSE)
check("evidence_dump detected", ft == "evidence_dump")

print("\n-- classify_failure_type: generic fallback --")
GENERIC_RESPONSE = "vague operations submitted, quality response not available"
ft2 = classify_failure_type("what was task 1", GENERIC_RESPONSE)
check("generic_quality_fallback detected", ft2 == "generic_quality_fallback")

print("\n-- log_failed_response writes entry --")
entry = log_failed_response(
    message="test_message_do_not_use",
    response="test bad response",
    reason="evidence_dump",
)
check("log returns dict", isinstance(entry, dict))
check("entry has failure_id", "failure_id" in entry)
check("entry has created_at", "created_at" in entry)
check("entry has user_message", entry.get("user_message") == "test_message_do_not_use")
check("entry has failure_type", entry.get("failure_type") == "evidence_dump")

print("\n-- generate_test_from_failure produces test spec --")
spec = generate_test_from_failure(entry)
check("spec is dict", isinstance(spec, dict))
check("spec has input_message", "input_message" in spec)
check("spec has expected_response_starts_with", "expected_response_starts_with" in spec)
check("spec has must_not_contain", "must_not_contain" in spec)
check("spec has failure_type", "failure_type" in spec)

print("\n-- format_failure_review runs without error --")
try:
    review = format_failure_review()
    check("format_failure_review returns string", isinstance(review, str))
    check("review has content", len(review) > 5)
except Exception as e:
    check(f"format_failure_review: {e}", False)

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
