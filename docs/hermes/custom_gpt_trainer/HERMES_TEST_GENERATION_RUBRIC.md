# Hermes Test Generation Rubric

Use this rubric to generate test cases from failed Hermes responses.

---

## Test Case Template

Every test case follows the `check(label, condition)` pattern used in `scripts/`.

```python
def check(label, cond):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}")
    return cond

# Given a message, test:
# 1. Intent classification
# 2. CFO brain activation
# 3. Response header
# 4. Required phrases present
# 5. Forbidden phrases absent
# 6. Approval boundary present
```

---

## Required Test Structure

For each failure scenario, generate:

### A. Intent Classification Test
```python
from lib.hermes_cfo_brain import classify_cfo_intent, should_use_cfo_brain

msg = "[user message here]"
intent = classify_cfo_intent(msg.lower(), context=None)
uses_brain = should_use_cfo_brain(msg)

check("intent classified correctly", intent == "[expected_intent]")
check("CFO brain activates", uses_brain is True)
```

### B. Response Header Test
```python
from lib.hermes_cfo_brain import process_with_cfo_brain

response = process_with_cfo_brain(msg)
check("response is not None", response is not None)
check("response has correct header", response.startswith("[EXPECTED_HEADER]"))
```

### C. No Evidence Dump Test
```python
EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:",
    "Confidence: ",
    "Source 1:",
    "artifact_inventory",
    "handoff_state",
    "HERMES REPORT",
]
for marker in EVIDENCE_DUMP_MARKERS:
    check(f"no marker: {marker!r}", marker not in (response or ""))
```

### D. Required Content Test
```python
REQUIRED_PHRASES = [
    "[phrase that must appear]",
]
for phrase in REQUIRED_PHRASES:
    check(f"contains: {phrase!r}", phrase.lower() in (response or "").lower())
```

### E. Approval Boundary Test
```python
check("approval boundary present", "explicit Ray approval" in (response or "").lower())
```

---

## Failure Type → Expected Intent Mapping

| Failure Type | User Message Pattern | Expected Intent |
|---|---|---|
| evidence_dump | "can you simplify your response" | simplify_previous_response |
| generic_quality_fallback | "what was task 1" | task_reference |
| wrong_tool | "what did you do this morning" | morning_activity_question |
| lost_context | "lets do 1" | option_selection |
| too_technical | "explain your recommendation in plain language" | explain_previous_response |
| did_not_assign_scout | "what did you do this morning" | morning_activity_question |

---

## Failure Type → Expected Header Mapping

| Failure Type | Expected Header |
|---|---|
| evidence_dump | `PLAIN ANSWER` (simplified version) |
| generic_quality_fallback | `PLAIN ANSWER` |
| wrong_tool (queue) | `TASK QUEUE` |
| wrong_tool (morning) | `MORNING SUMMARY` |
| wrong_tool (money) | `WEEKLY MONEY PLAN` |
| option_selection | `OPTION SELECTED` |
| scout dispatch | `I DON'T HAVE VERIFIED EVIDENCE YET` |
| failure feedback | `CORRECTING COURSE` |
| prompt generation | `IMPLEMENTATION PROMPT` |

---

## Test File Naming Convention

Test files live in `scripts/` and follow:
- `test_cfo_brain_[scenario].py` — tests for specific CFO brain scenarios
- `test_phase7b_[feature].py` — regression tests for Phase 7B features

## How to Use This Rubric

1. Paste a failed response into the Nexus CFO Trainer
2. Ask: "Generate a test case for this failure using the Hermes test generation rubric"
3. The trainer returns a `check(label, cond)` test block
4. Paste the test block into the appropriate `scripts/test_cfo_brain_*.py` file
5. Run: `python scripts/test_cfo_brain_failure_learning.py`
