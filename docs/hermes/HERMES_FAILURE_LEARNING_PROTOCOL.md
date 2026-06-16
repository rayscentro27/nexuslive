# Hermes Failure Learning Protocol

## Purpose

When Hermes produces a bad response, that failure should become a training example — not just a frustration.

## Trigger Phrases

Hermes should start failure logging when Ray says:
- "That is not what I meant"
- "That's wrong"
- "That's not right"
- "Wrong answer"
- "Log this as a bad response"
- "Hermes, learn from that"

## Hermes Response to Correction

When Ray says "that is not what I meant", Hermes should:

1. Apologize briefly (one sentence)
2. Infer or ask for the corrected intent
3. Log the failure with `log_failed_response()`
4. Offer to create a lesson or test case
5. Answer correctly

Format:
```
CORRECTING COURSE

I understand — that was not the right response.

What I think you actually wanted: <inferred correct intent>

Let me try again:
<correct response>

I logged this as a training example. Say "create tests from failures" to generate a test case.
```

## Failure Types

| Type | Description |
|------|-------------|
| evidence_dump | Response contained an artifact inventory or evidence section |
| generic_quality_fallback | Response was a generic "I wasn't sure" fallback |
| wrong_tool | Wrong handler was used for the message |
| lost_context | Follow-up question lost conversation context |
| failed_followup | Follow-up was not threaded to prior conversation |
| too_technical | Response was too long or technical |
| did_not_assign_scout | Unknown question not dispatched to scout |
| did_not_create_prompt | Prompt request not fulfilled |
| unsafe_action_attempt | Response attempted unsafe action |
| duplicate_queue_item | Research queue item was duplicated |

## File Storage

- Failed examples: `docs/reports/training/hermes_failed_response_examples.jsonl`
- Training set: `docs/reports/training/hermes_response_training_set.jsonl`

## Commands

- `log this as a bad response` → logs current interaction as failure
- `that was not what I meant` → logs failure + re-routes
- `hermes, learn from that` → logs failure + suggests lesson
- `show failed responses` → shows unreviewed failures
- `create tests from failures` → generates test cases from failures
