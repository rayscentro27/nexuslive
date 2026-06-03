# Hermes System Layer Audit

Timestamp: 20260603_164713

## Telegram bot entrypoint
- file path: telegram_bot.py
- line: 3327
- purpose: Primary inbound Telegram handler and top-level routing orchestration.
- state: active
- read sources: docs/reports/actions/hermes_action_queue.jsonl
- write targets: docs/reports/actions/hermes_action_queue.jsonl
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: Routing collisions from multiple legacy layers., Memory pre-check can preempt newer layers.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: False

## telegram_bot.py routing order
- file path: telegram_bot.py
- line: 3327
- purpose: Pre-router order for memory commands, CFO phases, continuity, TelegramRouter, and shadow logging.
- state: active
- read sources: docs/reports/actions/hermes_action_queue.jsonl
- write targets: docs/reports/actions/hermes_action_queue.jsonl
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: False

## Command intake
- file path: hermes_command_router/intake.py
- line: 622
- purpose: Deterministic phrase-to-intent normalization and approval flags.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Command router
- file path: hermes_command_router/router.py
- line: 3546
- purpose: Maps normalized intents to plain handlers, reports, or model-backed fallback.
- state: active
- read sources: docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/artifact_registry/nexus_artifact_registry.jsonl, docs/reports/ceo_review/, docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_, docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/hermes_decisions/, docs/reports/hermes_decisions/hermes_decision_log.jsonl, docs/reports/hermes_handoffs/, docs/reports/hermes_handoffs/handoff_, docs/reports/hermes_proactive_notifications.jsonl, docs/reports/intake/telegram_source_intake.jsonl, docs/reports/knowledge_gaps/hermes_knowledge_gaps.jsonl, docs/reports/memory/learning/hermes_lesson_proposals.jsonl, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/premium_blockers/, docs/reports/premium_blockers/blocker_resolution_beehiiv_, docs/reports/ray_feedback/, docs/reports/revenue_packets/latest_revenue_asset_packet.json, docs/reports/youtube/source_registry.json, hermes_memory_v2
- write targets: docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/artifact_registry/nexus_artifact_registry.jsonl, docs/reports/ceo_review/, docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_, docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/hermes_decisions/, docs/reports/hermes_decisions/hermes_decision_log.jsonl, docs/reports/hermes_handoffs/, docs/reports/hermes_handoffs/handoff_, docs/reports/hermes_proactive_notifications.jsonl, docs/reports/intake/telegram_source_intake.jsonl, docs/reports/knowledge_gaps/hermes_knowledge_gaps.jsonl, docs/reports/memory/learning/hermes_lesson_proposals.jsonl, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/premium_blockers/, docs/reports/premium_blockers/blocker_resolution_beehiiv_, docs/reports/ray_feedback/, docs/reports/revenue_packets/latest_revenue_asset_packet.json, docs/reports/youtube/source_registry.json
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: Non-plain intents can still use HERMES REPORT wrapper., Some handlers can touch network-backed providers.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: False

## Phase 6 daily operating cycle
- file path: lib/hermes_daily_operating_cycle.py
- line: 374
- purpose: Builds today's internal plan, top revenue move, blockers, and approval summaries.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Daily cycle state
- file path: lib/hermes_daily_cycle_state.py
- line: 12
- purpose: Stores latest daily cycle state, history, pending items, and plan comparisons.
- state: active
- read sources: docs/reports/operations/hermes_daily_cycle_history.jsonl, docs/reports/operations/hermes_daily_cycle_state.json
- write targets: docs/reports/operations/hermes_daily_cycle_history.jsonl, docs/reports/operations/hermes_daily_cycle_state.json
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Approval queue
- file path: lib/hermes_approval_queue.py
- line: 3
- purpose: Normalizes local approval items and supports local approve/reject/safety impact workflows.
- state: active
- read sources: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_history.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/memory/hermes_lessons.jsonl, docs/reports/operations/hermes_daily_cycle_state.json
- write targets: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_history.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/memory/hermes_lessons.jsonl, docs/reports/operations/hermes_daily_cycle_state.json
- safety boundary: Approve authorizes next step only; no publish/email/spend/deploy/trade execution.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Revenue asset packet
- file path: lib/hermes_revenue_asset_packet.py
- line: 2
- purpose: Builds and scores revenue packet assets and approval candidates.
- state: active
- read sources: docs/reports/content/, docs/reports/content/fixed/, docs/reports/revenue_packets/
- write targets: docs/reports/content/, docs/reports/content/fixed/, docs/reports/revenue_packets/
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Funnel packet / launch packet
- file path: docs/reports/funnel/
- line: None
- purpose: Internal report artifacts for launch/funnel approval packets; not a live routing module.
- state: legacy
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: False
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Learning loop
- file path: lib/hermes_learning_loop.py
- line: 3
- purpose: Captures lesson proposals locally and, after explicit approval, can write to hermes_memory_v2.
- state: active
- read sources: hermes_memory_v2
- write targets: none found
- safety boundary: Pending proposals local only; approved lesson writes require Ray approval and target hermes_memory_v2 only.
- known risks: Approved lessons can write Supabase., Proposal file may accumulate stale items.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: True

## Memory v2 reader
- file path: lib/hermes_memory_v2_reader.py
- line: 2
- purpose: Preview-only structured memory reader for active/live_answer rows.
- state: preview
- read sources: hermes_memory_v2
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: Supabase credential dependence., Preview-only can diverge from live truth.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: False

## Memory v2 primary mode
- file path: lib/hermes_memory_v2_shadow.py
- line: 3
- purpose: Mode gates preview/shadow/primary behavior for memory v2 with strong approval guards.
- state: preview
- read sources: docs/reports/memory/hermes_memory_v2_primary_approval.json
- write targets: docs/reports/memory/hermes_memory_v2_primary_approval.json
- safety boundary: Primary mode requires explicit approval file and guard checks.
- known risks: Guarded primary may be requested but not actually active., Shadow/preview drift can confuse operators.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## CFO brain Phase 7
- file path: lib/hermes_cfo_brain.py
- line: 171
- purpose: Handles follow-up reasoning, option selection, explain/simplify, failure feedback, and selected strategy responses.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Conversation state manager
- file path: lib/hermes_conversation_state.py
- line: 307
- purpose: Persists last options, selected option, recommendation, artifact path, and meaningful response context.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Plain-language rewriter
- file path: lib/hermes_plain_language_rewriter.py
- line: None
- purpose: Rewrites or compresses complex outputs into operator-friendly plain language.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Failure learning
- file path: lib/hermes_failure_learning.py
- line: 9
- purpose: Logs bad responses and generates learn/test artifacts from failures.
- state: active
- read sources: docs/reports/training/hermes_failed_response_examples.jsonl, docs/reports/training/hermes_response_training_set.jsonl
- write targets: docs/reports/training/hermes_failed_response_examples.jsonl, docs/reports/training/hermes_response_training_set.jsonl
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Custom GPT trainer package
- file path: docs/hermes/custom_gpt_trainer/
- line: None
- purpose: Documentation/training package for response rewrite, failure review, and alignment prompts.
- state: legacy
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: False
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Phase 8A CFO prototype
- file path: prototypes/hermes_agentic_cfo_loop.py
- line: 1193
- purpose: Prototype agentic CFO loop with intent/retrieval/reasoning/tool/plain-language stages.
- state: prototype-only
- read sources: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- write targets: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: Prototype mock markers exist in codebase., Not safe as full live primary without guards.
- can affect live Telegram response: True
- uses mock data: True
- can call network/model providers: False
- can write Supabase: False

## Phase 8B shadow mode
- file path: lib/hermes_cfo_loop_shadow.py
- line: 3
- purpose: Runs CFO loop in background and logs traces without changing live response.
- state: inactive
- read sources: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- write targets: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: Trace volume can obscure latest state., Prototype output still exists in shadow path.
- can affect live Telegram response: True
- uses mock data: True
- can call network/model providers: False
- can write Supabase: False

## Phase 8C limited primary mode
- file path: lib/hermes_cfo_loop_shadow.py
- line: 42
- purpose: Allows grounded, allowlisted CFO responses to become live Telegram answers.
- state: inactive
- read sources: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- write targets: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- safety boundary: Allowlisted intents only; hard blocked/risky intents never become primary.
- known risks: Allowlisted intents only; anything outside falls to legacy routing., Grounding depends on local state quality.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Phase 8C.1 grounded limited primary guard
- file path: lib/hermes_cfo_loop_shadow.py
- line: 89
- purpose: Blocks mock/sample output and requires grounded evidence paths before primary use.
- state: active
- read sources: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- write targets: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/content/, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/research_queue/hermes_research_queue.jsonl, docs/reports/research_queue/hermes_scout_assignments.jsonl, docs/reports/scouts/, docs/reports/strategy/, docs/reports/strategy/hermes_conversation_state.json
- safety boundary: Blocks mock/sample output and ungrounded primary answers.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Scout assignments
- file path: lib/hermes_scout_dispatcher.py
- line: 250
- purpose: Creates scout dispatch handoffs and logs scout dispatch artifacts.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: False
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Research queue
- file path: hermes_command_router/router.py
- line: 2971
- purpose: Read-only queue review, dedupe, assignment visibility, and unresolved question surfacing.
- state: active
- read sources: docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/artifact_registry/nexus_artifact_registry.jsonl, docs/reports/ceo_review/, docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_, docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/hermes_decisions/, docs/reports/hermes_decisions/hermes_decision_log.jsonl, docs/reports/hermes_handoffs/, docs/reports/hermes_handoffs/handoff_, docs/reports/hermes_proactive_notifications.jsonl, docs/reports/intake/telegram_source_intake.jsonl, docs/reports/knowledge_gaps/hermes_knowledge_gaps.jsonl, docs/reports/memory/learning/hermes_lesson_proposals.jsonl, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/premium_blockers/, docs/reports/premium_blockers/blocker_resolution_beehiiv_, docs/reports/ray_feedback/, docs/reports/revenue_packets/latest_revenue_asset_packet.json, docs/reports/youtube/source_registry.json, hermes_memory_v2
- write targets: docs/reports/approvals/hermes_approval_queue_state.json, docs/reports/artifact_registry/nexus_artifact_registry.jsonl, docs/reports/ceo_review/, docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_, docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/hermes_decisions/, docs/reports/hermes_decisions/hermes_decision_log.jsonl, docs/reports/hermes_handoffs/, docs/reports/hermes_handoffs/handoff_, docs/reports/hermes_proactive_notifications.jsonl, docs/reports/intake/telegram_source_intake.jsonl, docs/reports/knowledge_gaps/hermes_knowledge_gaps.jsonl, docs/reports/memory/learning/hermes_lesson_proposals.jsonl, docs/reports/operations/hermes_daily_cycle_state.json, docs/reports/premium_blockers/, docs/reports/premium_blockers/blocker_resolution_beehiiv_, docs/reports/ray_feedback/, docs/reports/revenue_packets/latest_revenue_asset_packet.json, docs/reports/youtube/source_registry.json
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: False

## Action queue
- file path: lib/hermes_action_queue.py
- line: 4
- purpose: Append-only local action tracker for opportunities, approvals, scouts, and artifacts.
- state: active
- read sources: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/actions/hermes_action_queue_latest.md
- write targets: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/actions/hermes_action_queue_latest.md
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Decision log
- file path: lib/hermes_decision_log.py
- line: 2
- purpose: Stores decision artifacts and feeds approval queue / recent decision views.
- state: active
- read sources: docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/decisions/hermes_decision_log_latest.md
- write targets: docs/reports/decisions/hermes_decision_log.jsonl, docs/reports/decisions/hermes_decision_log_latest.md
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Evidence/artifact fallback
- file path: lib/hermes_internal_first.py
- line: None
- purpose: Builds internal evidence-based fallback answers from local artifacts and handoffs.
- state: active
- read sources: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/content/, docs/reports/core/nexus_project_brief.md, docs/reports/handoffs/, docs/reports/handoffs/., docs/reports/intake/telegram_source_intake.jsonl, docs/reports/monetization/, docs/reports/monetization/., docs/reports/trading/
- write targets: docs/reports/actions/hermes_action_queue.jsonl, docs/reports/content/, docs/reports/core/nexus_project_brief.md, docs/reports/handoffs/, docs/reports/handoffs/., docs/reports/intake/telegram_source_intake.jsonl, docs/reports/monetization/, docs/reports/monetization/., docs/reports/trading/
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: Can produce artifact dumps instead of operator answer., May surface stale handoff-heavy summaries.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Old HERMES REPORT wrapper
- file path: hermes_command_router/report.py
- line: 14
- purpose: Wraps non-plain router outputs into HERMES REPORT structure.
- state: legacy
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Quality fallback
- file path: lib/hermes_response_quality.py
- line: 261
- purpose: Last-resort fallback text when response quality checks fail.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: Generic low-signal answer if upstream path fails.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: False
- can write Supabase: False

## Provider/gateway layer
- file path: lib/hermes_model_router.py
- line: 82
- purpose: Chooses/synthesizes provider-backed model calls for non-plain command router paths.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.
- known risks: none noted
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: False

## TelegramRouter / LLM fallback
- file path: lib/telegram_router.py
- line: 81
- purpose: Secondary Telegram routing for approvals, strategic regexes, commands, report requests, and generic conversational fallback.
- state: active
- read sources: none found
- write targets: none found
- safety boundary: Can still fall through to conversational/model layer when earlier layers do not intercept.
- known risks: Can trigger evidence dumps or model fallback if higher-order layers miss.
- can affect live Telegram response: True
- uses mock data: False
- can call network/model providers: True
- can write Supabase: False
