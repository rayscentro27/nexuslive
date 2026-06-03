# Hermes Data Source Audit

Timestamp: 20260603_164713

## docs/reports/strategy/hermes_conversation_state.json
- read by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- written by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/operations/hermes_daily_cycle_state.json
- read by: Approval queue, Command router, Daily cycle state, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Research queue
- written by: Approval queue, Command router, Daily cycle state, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Research queue
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/actions/hermes_action_queue.jsonl
- read by: Action queue, Approval queue, Evidence/artifact fallback, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Telegram bot entrypoint, telegram_bot.py routing order
- written by: Action queue, Approval queue, Evidence/artifact fallback, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Telegram bot entrypoint, telegram_bot.py routing order
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/approvals/hermes_approval_queue_state.json
- read by: Approval queue, Command router, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Research queue
- written by: Approval queue, Command router, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Research queue
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/research_queue/hermes_research_queue.jsonl
- read by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- written by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/research_queue/hermes_scout_assignments.jsonl
- read by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- written by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/decisions/hermes_decision_log.jsonl
- read by: Approval queue, Command router, Decision log, Research queue
- written by: Approval queue, Command router, Decision log, Research queue
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/content/
- read by: Evidence/artifact fallback, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Revenue asset packet
- written by: Evidence/artifact fallback, Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard, Revenue asset packet
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: high
- duplicate risk: high
- source of truth: active

## docs/reports/funnel/
- read by: none
- written by: none
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: high
- duplicate risk: high
- source of truth: legacy/reference only

## docs/reports/scouts/
- read by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- written by: Phase 8A CFO prototype, Phase 8B shadow mode, Phase 8C limited primary mode, Phase 8C.1 grounded limited primary guard
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: high
- duplicate risk: high
- source of truth: active

## docs/reports/strategy/shadow/hermes_cfo_loop_shadow_traces.jsonl
- read by: none
- written by: none
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: legacy/reference only

## docs/reports/training/hermes_failed_response_examples.jsonl
- read by: Failure learning
- written by: Failure learning
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/reports/training/hermes_response_training_set.jsonl
- read by: Failure learning
- written by: Failure learning
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## docs/hermes/
- read by: none
- written by: none
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: legacy/reference only

## docs/hermes/custom_gpt_trainer/
- read by: none
- written by: none
- safe/unsafe: safe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: legacy/reference only

## hermes_memory_v2
- read by: Command router, Learning loop, Memory v2 reader, Research queue
- written by: none
- safe/unsafe: unsafe
- contains secrets: no
- contains private client data: unknown
- stale risk: medium
- duplicate risk: medium
- source of truth: active

## old memory / task / agent / approval tables
- read by: none
- written by: none
- safe/unsafe: unsafe
- contains secrets: no
- contains private client data: unknown
- stale risk: high
- duplicate risk: high
- source of truth: legacy/reference only
