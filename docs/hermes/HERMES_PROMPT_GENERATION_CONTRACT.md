# Hermes Prompt Generation Contract

## When to Generate

Generate an implementation prompt when:
1. Ray says "create a prompt for Claude to fix this"
2. Ray says "give me a prompt for Claude to build this"
3. Ray says "what should I send Claude?"
4. Ray says "create a super prompt"
5. Ray says "turn this into a Claude prompt"
6. Ray is about to hand work to Claude Code / OpenCode

## Required Format

```
IMPLEMENTATION PROMPT

Goal: <what needs to be built or fixed>

Context: <relevant Hermes state, prior work, constraints>

Requirements:
  - Follow existing Hermes architecture (intake → router → handler)
  - Add to _PLAIN_INTENTS and _EVIDENCE_DUMP_BLOCKED_PHRASES
  - Write tests in scripts/ following the check(label, cond) pattern
  - No publishing, no emails, no spending, no Supabase writes

Safety:
  I will not publish, email subscribers, sell, deploy, spend money,
  apply to affiliate programs, activate Stripe, run live trading, or
  use client-facing content without explicit Ray approval.

Tests:
  - Intent classification test
  - Response header test
  - Safety language test
  - No evidence dump test

Final report:
  - Files changed
  - Tests run and results
  - Supabase writes: expected NO
  - Old tables changed: expected NO
  - Commit hash
```

## What to Include in Context

- Current revenue packet score (if relevant)
- Active approval queue items (if relevant)
- Phase number and what was just built
- Files that need to be modified
- Existing patterns to follow

## What NOT to Include

- Raw credentials or API keys
- Personal client data
- Private strategy notes
- Supabase connection strings
