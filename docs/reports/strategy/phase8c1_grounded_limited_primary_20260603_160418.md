# Phase 8C1 Grounded Limited Primary

Timestamp: 2026-06-03 16:04:18 America/Phoenix

## Root Cause

Limited primary grounding was incomplete in two places:

1. The CFO loop could still pass through mock or sample phrases if the response was not explicitly blocked.
2. Telegram routing ran `_try_memory_command()` before the Phase 8C intercept, so some phrases such as `what changed in the draft` were swallowed by older memory-command handlers and never reached grounded limited primary.

There was also a state-quality issue:

- `create the implementation prompt now` could reuse a stale generic selected option (`Research the question and return with verified evidence`) even when the active live recommendation was more relevant.

## Files Changed

- `lib/hermes_cfo_loop_shadow.py`
- `prototypes/hermes_agentic_cfo_loop.py`
- `telegram_bot.py`
- `scripts/test_phase8c_grounding_blocks_mock_primary.py`
- `scripts/test_phase8c_summary_of_day_requires_real_state.py`
- `scripts/test_phase8c_scout_status_requires_real_assignments.py`
- `scripts/test_phase8c_approval_bulk_uses_real_queue.py`
- `scripts/test_phase8c_implementation_prompt_uses_selected_option.py`
- `scripts/test_phase8c_draft_comparison_context_or_clarify.py`
- `scripts/test_phase8c_clarifying_question_primary.py`
- `scripts/test_phase8c_existing_commands_still_work.py`

## Mock-Output Guard

Primary responses are now blocked if the CFO output contains any of:

- `Based on mock data`
- `sample`
- `mock`
- `Mailchimp opt-in form`
- `Build and publish lead magnet landing page`
- `Connect affiliate offer link`
- `research_scout_1`
- `draft v2 approved`

If blocked, limited primary falls back instead of using that response.

## Grounded Data Paths

Grounded status reporting and allowlisted intents now check these local paths:

- `docs/reports/strategy/hermes_conversation_state.json`
- `docs/reports/operations/hermes_daily_cycle_state.json`
- `docs/reports/actions/hermes_action_queue.jsonl`
- `docs/reports/approvals/hermes_approval_queue_state.json`
- `docs/reports/research_queue/hermes_research_queue.jsonl`
- `docs/reports/research_queue/hermes_scout_assignments.jsonl`
- `docs/reports/content/`
- `docs/reports/strategy/`
- `docs/reports/scouts/`

Intent grounding behavior:

- `implementation_prompt_request`: uses selected option or active recommendation; asks what to implement if missing.
- `approval_bulk_request`: uses live approval queue or reports unavailable.
- `scout_status`: uses live assignments / research queue / action queue or reports unavailable.
- `summary_of_day`: uses live daily state and recent local reports or reports unavailable.
- `draft_comparison`: uses real draft paths or asks which draft to compare.
- `plain_language_followup`: uses last meaningful response only.
- `acknowledgement_check`: unchanged and safe.

## Routing Fixes

- `ask me a better clarifying question` now returns the Phase 8C clarifying-question primary response.
- `what changed in the draft` now reaches grounded draft comparison before older memory-command routing and no longer falls into daily-plan comparison.

## Status Command

`show cfo limited primary status` now reports:

- primary used count
- mock-blocked count
- grounded count
- fallback count
- allowlisted intents
- grounded data paths checked

## Tests Run

Passed:

- `python3 scripts/test_phase8c_grounding_blocks_mock_primary.py`
- `python3 scripts/test_phase8c_summary_of_day_requires_real_state.py`
- `python3 scripts/test_phase8c_scout_status_requires_real_assignments.py`
- `python3 scripts/test_phase8c_approval_bulk_uses_real_queue.py`
- `python3 scripts/test_phase8c_implementation_prompt_uses_selected_option.py`
- `python3 scripts/test_phase8c_draft_comparison_context_or_clarify.py`
- `python3 scripts/test_phase8c_clarifying_question_primary.py`
- `python3 scripts/test_phase8c_existing_commands_still_work.py`

## Live Validation

Validated through `NexusTelegramBot.handle_inbound_message(...)` with `HERMES_CFO_LOOP_MODE=limited_primary`:

1. `show cfo limited primary status`
2. `what did we work on today`
3. `what are all the scouts doing right now`
4. `i approve them all`
5. `create the implementation prompt now`
6. `what changed in the draft`
7. `ask me a better clarifying question`
8. `show memory v2 primary status`
9. `Hermes, run daily operating cycle`

Observed:

- no `Based on mock data`
- no sample scout names such as `research_scout_1`
- grounded limited-primary responses for the allowlisted intents
- exact legacy commands still working
- no Supabase writes triggered by this patch

## Telegram Restart

- launchd label: `com.raymonddavis.nexus.telegram`
- restart command: `launchctl kickstart -k gui/501/com.raymonddavis.nexus.telegram`
- active PID after restart: `44631`

## Safety

- Supabase changed: NO
- old tables changed: NO
- publish/email/spend/deploy/payment/affiliate activation/live trading: NO

## Commit

- commit hash: PENDING
- push status: not pushed
