# Hermes Full System Audit Summary

Timestamp: 20260603_164713

## Executive Summary
Hermes currently runs a stacked routing architecture: Telegram pre-checks, command-router plain intents, CFO conversation/brain layers, Phase 8 limited-primary grounding, and TelegramRouter/model fallback. Multiple older fallback paths still exist and can collide when newer intercepts are off.

## Current Active Architecture
- Telegram bot entrypoint
- telegram_bot.py routing order
- Command intake
- Command router
- Phase 6 daily operating cycle
- Daily cycle state
- Approval queue
- Revenue asset packet
- Learning loop
- Memory v2 reader
- Memory v2 primary mode
- CFO brain Phase 7
- Conversation state manager
- Plain-language rewriter
- Failure learning
- Phase 8C.1 grounded limited primary guard
- Scout assignments
- Research queue
- Action queue
- Decision log
- Evidence/artifact fallback
- Quality fallback
- Provider/gateway layer
- TelegramRouter / LLM fallback

## Live Telegram Routing Order
1. Memory command pre-check
2. Inbound normalization
3. CFO shadow command exact handler
4. Phase 8C limited primary intercept
5. Phase 7C forced intents
6. Continuity exact command map
7. CFO conversation intercept
8. CFO brain general intercept
9. TelegramRouter
10. Command router
11. Evidence/artifact fallback
12. Quality fallback
13. Send response
14. Shadow trace / memory shadow logging

## Command Inventory Count
1108

## Active Commands By Category
- CFO loop status: 10
- approval: 89
- content draft: 17
- daily plan: 156
- fallback/help/small talk: 31
- learning: 59
- memory: 75
- revenue/funnel: 77
- scouts/research: 62
- shadow/primary mode: 16
- summaries: 398
- system health: 118

## Top 10 Broken or Risky Paths
- Memory command pre-check can still preempt newer layers.
- Legacy TelegramRouter conversational fallback can still hit evidence/model paths.
- Old HERMES REPORT wrapper still exists for non-plain command-router intents.
- Learning loop is the active Supabase-write path.
- Email/report router paths still exist in TelegramRouter.
- Revenue/funnel artifacts are spread across report folders and modules.
- Shadow/preview/primary terminology differs between memory v2 and CFO loop.
- Evidence fallback can still surface stale artifact-heavy summaries.
- Approval concepts exist in approval queue, learning loop, and conversational approvals.
- Prototype CFO loop code still contains mock/stale markers even though primary guard blocks them.

## Top 10 Cleanup Recommendations
- Unify all live Telegram routing into one documented precedence chain.
- Keep _try_memory_command narrow and explicit.
- Deprecate or isolate old HERMES REPORT wrapper paths.
- Add a single command registry as source of truth.
- Separate read-only audit-safe handlers from write-capable handlers.
- Move funnel/launch packet logic from artifact-only reports into explicit modules or mark it archival.
- Reduce generic evidence fallback for operator-facing questions.
- Consolidate approval semantics across approval queue and learning loop.
- Mark prototype/mock files more aggressively as non-live.
- Keep Phase 8C grounding tests as required regression gates.

## Main Answer
Each Hermes layer currently either intercepts live Telegram input, builds internal plan/approval context, or acts as a fallback/reporting path. The critical live-answer layers are telegram_bot pre-checks, Phase 8C limited primary, CFO conversation/brain, plain command-router handlers, and TelegramRouter fallback.
