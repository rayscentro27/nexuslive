# Hermes Routing Order Audit

Timestamp: 20260603_164713

## Actual Live Telegram Order
1. Memory command pre-check
   function: NexusTelegramBot._try_memory_command
   file: telegram_bot.py:3281
   catches: memory commands, approval queue read commands, daily plan read commands, learning loop commands
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: before
2. Inbound normalization
   function: _normalize_telegram_command
   file: telegram_bot.py:83
   catches: all text
   overrides later layers: False
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: before
3. CFO shadow command exact handler
   function: handle_cfo_shadow_command
   file: lib/hermes_cfo_loop_shadow.py:714
   catches: show cfo shadow status, show cfo limited primary status, rollback cfo loop to shadow
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: before
4. Phase 8C limited primary intercept
   function: run_cfo_limited_primary
   file: lib/hermes_cfo_loop_shadow.py:3295
   catches: allowlisted grounded CFO intents
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: self
5. Phase 7C forced intents
   function: process_with_cfo_brain
   file: telegram_bot.py:3588
   catches: option selection, task reference, simplify/explain, morning activity, failure feedback
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: after
6. Continuity exact command map
   function: continuity[...] -> _dispatch_continuity
   file: telegram_bot.py:3348
   catches: exact Telegram-only phrases and follow-ups
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: after
7. CFO conversation intercept
   function: build_cfo_response
   file: telegram_bot.py:3642
   catches: high-priority strategic conversation
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: after
8. CFO brain general intercept
   function: process_with_cfo_brain
   file: telegram_bot.py:3666
   catches: general CFO natural-language reasoning
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: after
9. TelegramRouter
   function: TelegramRouter.route_incoming_message
   file: lib/telegram_router.py:81
   catches: approval replies, risky action requests, strategic regex routes, command mode, report requests, daily plan, generic chat
   overrides later layers: True
   evidence dump risk: True
   quality fallback risk: True
   Phase 8C position: after
10. Command router
   function: run_command
   file: hermes_command_router/router.py:3546
   catches: normalized command intents
   overrides later layers: True
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: after
11. Evidence/artifact fallback
   function: try_internal_first / evidence-only chat fallback
   file: lib/hermes_internal_first.py:94
   catches: generic strategy/fallback questions
   overrides later layers: False
   evidence dump risk: True
   quality fallback risk: False
   Phase 8C position: after
12. Quality fallback
   function: hermes_response_quality fallback
   file: lib/hermes_response_quality.py:261
   catches: failed/gated responses
   overrides later layers: False
   evidence dump risk: False
   quality fallback risk: True
   Phase 8C position: after
13. Send response
   function: handle_inbound_message return
   file: telegram_bot.py:3747
   catches: all finalized answers
   overrides later layers: False
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: after
14. Shadow trace / memory shadow logging
   function: trigger_shadow_comparison_async / run_cfo_shadow_async
   file: telegram_bot.py:3726
   catches: all messages when shadow modes are enabled
   overrides later layers: False
   evidence dump risk: False
   quality fallback risk: False
   Phase 8C position: after

## Routing Collisions
- what changed in the draft vs daily plan comparison: Phase 8C now wins in limited_primary because _try_memory_command explicitly yields to allowlisted Phase 8C intents.
- approve all approvals vs lesson bulk approval: Potential overlap remains because 'approve all' style phrases exist in multiple approval systems; current mitigation relies on exact intent patterns.
- implementation prompt now vs evidence fallback: Grounded limited_primary now handles the phrase in limited_primary mode; legacy fallback still exists when Phase 8C is off.
- scout status vs source intake dump: Grounded limited_primary now wins in limited_primary mode; outside that mode, generic evidence fallback can still dump intake-heavy responses.
- approval safety vs approval queue: Different phrases hit different paths; conversational 'i approve them all' resolves to Phase 8C in limited_primary.
- summary of day vs generic strategy: Limited_primary path is grounded; without it, strategy/evidence fallback remains possible.
- launch packet review vs generic strategy: Unresolved overlap; should stay in audit recommendations.
- clarifying question vs evidence fallback: Resolved in limited_primary; older fallback still exists when Phase 8C is not active.
