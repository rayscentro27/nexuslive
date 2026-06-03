# Nexus CFO Trainer — Knowledge Manifest

## What the Trainer Knows

This document lists the knowledge files that should be uploaded to the Nexus CFO Trainer custom GPT.

### Core Doctrine Files

| File | Purpose |
|------|---------|
| `HERMES_CFO_CONVERSATION_CONTRACT.md` | Rules for how Hermes conducts CFO conversations |
| `HERMES_PLAIN_LANGUAGE_STYLE_GUIDE.md` | How to format plain-language responses |
| `HERMES_UNKNOWN_ANSWER_PROTOCOL.md` | What to do when Hermes doesn't know the answer |
| `HERMES_SCOUT_DISPATCH_CONTRACT.md` | How to dispatch scouts for research |
| `HERMES_PROMPT_GENERATION_CONTRACT.md` | How to create implementation prompts for Claude |
| `HERMES_FAILURE_LEARNING_PROTOCOL.md` | How to log and learn from bad responses |

### Trainer-Specific Files

| File | Purpose |
|------|---------|
| `NEXUS_CFO_TRAINER_GPT_INSTRUCTIONS.md` | Role and operating modes for the trainer GPT |
| `HERMES_FAILURE_REVIEW_PROMPT.md` | Structured prompt for reviewing failed responses |
| `HERMES_RESPONSE_REWRITE_RUBRIC.md` | Rubric for rewriting bad responses |
| `HERMES_TEST_GENERATION_RUBRIC.md` | Rubric for generating test cases |
| `HERMES_ACTIONS_API_PLAN.md` | Plan for connecting trainer to live Hermes state |

## Live Data Sources (Future)

When the Hermes Actions API is live, the trainer will be able to pull:
- `hermes_failed_response_examples.jsonl` — unreviewed failure examples
- `hermes_response_training_set.jsonl` — approved training examples
- Current revenue packet score
- Current approval queue items

Until then, Ray pastes data directly into the trainer chat.

## What the Trainer Does NOT Know

- Live Supabase data
- Current revenue numbers (exact)
- Active client information
- API keys, credentials, or secrets
- Internal IP addresses or deployment configs

## Version

Trainer Knowledge Version: 7B.0
Last updated: 2026-06-03
Phase: Phase 7B — CFO Brain and Trainer Architecture
