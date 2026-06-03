# Hermes Failure Review Prompt

Use this prompt to ask the Nexus CFO Trainer to review a failed Hermes response.

---

## Template

Paste this into the Nexus CFO Trainer chat and fill in the bracketed sections:

```
HERMES FAILURE REVIEW

User message:
[paste the message Ray sent]

Hermes response (bad):
[paste the bad response Hermes gave]

What Ray actually wanted:
[describe what the right response should have been, if known]

Review this failure:
1. What failure type is this? (evidence_dump / generic_quality_fallback / wrong_tool / lost_context / too_technical / did_not_assign_scout / did_not_create_prompt)
2. What rule did Hermes violate?
3. Rewrite the response correctly.
4. Generate a test case spec for this failure.
```

---

## Example: Failure #1 — Simplify Request

**User message:**
CAN YOU SIMPLIFY YOUR RESPONSE

**Hermes response (bad):**
```
HERMES REPORT
═══════════════════════════════════

artifact_inventory:
  - revenue_asset_packet.json (score: 72)
  - approval_queue.json (3 items)
  - research_queue.json (2 gaps)

Live answer sources:
  - Executive Memory v2: accessed
  - Daily Operating Cycle: last run 06:00

Confidence: MEDIUM
```

**What Ray actually wanted:**
A shorter, plain-language version of the previous response.

---

## Example: Failure #2 — Task Reference

**User message:**
WHAT WAS TASK 1

**Hermes response (bad):**
I'm not entirely sure which task you're referring to. Based on what I have available, I could not locate a specific task labeled "1" in the current system state. You may want to run the daily operating cycle for the most current task list.

**What Ray actually wanted:**
Hermes should have looked up option/task 1 from the numbered list it gave in the last response.

---

## How to Use Failure Review Results

1. The trainer generates a test case spec → paste into `scripts/test_cfo_brain_*.py`
2. The trainer rewrites the response → compare to actual Hermes output
3. If Hermes still gives the bad response → identify the pattern to add to intent classifier
4. Log the resolved failure with `suggest_training_example()` from `lib/hermes_failure_learning.py`
