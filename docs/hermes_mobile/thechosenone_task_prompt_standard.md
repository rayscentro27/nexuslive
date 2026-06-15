# TheChoseone Task Prompt Standard

Every backend task Hermes hands to TheChoseone uses this one format, so tasks are
unambiguous, safe, and routable. Built by
`lib/hermes_to_thechosenone_prompt_builder.py`.

## Format
```
Task: <one sentence>

Goal: <business outcome>

Context: <only safe, relevant context>

Inputs:
* <known input>

Required output:
* <artifact / report expected>
* <decision needed>

Safety:
* Do not expose secrets.
* Do not send emails/DMs.
* Do not publish.
* Do not approve.
* Do not trade live.
* Do not charge.
* Do not deploy.
* Do not use paid APIs unless explicitly approved.

Success criteria: <measurable result>

Suggested route:
<research | showroom | proof_automation | codex | claude | opencode | internal_script | manual_review>
```

## Rules
- **Task is one sentence.** Goal is the business outcome, not the mechanics.
- **Context is safe-only** — never paste tokens, chat ids, account numbers, or
  private identifiers. The builder scrubs obvious secrets automatically.
- **The Safety block is always present and verbatim** (`SAFETY_BLOCK`).
- **Suggested route** is validated against the allowed set; an unknown route is
  replaced by `suggest_route()`'s best guess (never an invalid route).

## API
- `build_task_prompt(task, goal, context="", inputs=None, required_output=None, success_criteria="", route=None)`
- `build_research_prompt(topic)` — convenience for public-info questions.
- `suggest_route(text)` — best-guess route from free text.
- `ROUTES`, `SAFETY_BLOCK` — the allowed routes and the standing safety lines.

Tests: `tests/test_hermes_to_thechosenone_prompt_builder.py`.
