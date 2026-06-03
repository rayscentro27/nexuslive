# Hermes Safety / Approval Audit

Timestamp: 20260603_164713

## publish / client-facing content
- function: _risky_action_requested / approval gating / approval queue category filters
- file: telegram_bot.py / lib/hermes_approval_queue.py
- current behavior: Requires approval or stays internal only.
- approval required: True
- approval boundary shown: True
- blocked correctly: True
- risk level: high
- recommendation: Keep blocked; do not let conversational fallbacks imply publication.

## subscriber email
- function: TelegramRouter report/knowledge email paths; approval queue high-risk categories
- file: lib/telegram_router.py / lib/hermes_approval_queue.py
- current behavior: Email-capable path still exists in router; approval queue treats subscriber email as high risk.
- approval required: True
- approval boundary shown: True
- blocked correctly: False
- risk level: high
- recommendation: Audit/disable live email-send paths before future feature work.

## affiliate application / link activation
- function: Approval queue high-risk categories and CFO hard-blocked intents
- file: lib/hermes_approval_queue.py / lib/hermes_cfo_loop_shadow.py
- current behavior: Primary responses blocked; explicit activation should require approval.
- approval required: True
- approval boundary shown: True
- blocked correctly: True
- risk level: high
- recommendation: Keep only placeholder/internal references.

## Stripe/payment activation
- function: Approval queue high-risk categories and CFO hard-blocked intents
- file: lib/hermes_approval_queue.py / lib/hermes_cfo_loop_shadow.py
- current behavior: Blocked from safe approval bulk flows and primary mode.
- approval required: True
- approval boundary shown: True
- blocked correctly: True
- risk level: high
- recommendation: Keep separate from internal drafts and research.

## deploy production
- function: Risky action approval gate and approval queue categories
- file: telegram_bot.py / lib/hermes_approval_queue.py
- current behavior: Should require approval and not execute automatically from Hermes flows.
- approval required: True
- approval boundary shown: True
- blocked correctly: True
- risk level: high
- recommendation: Keep deployment outside Hermes conversational surface.

## spend money
- function: Approval queue and CFO hard-blocked intents
- file: lib/hermes_approval_queue.py / lib/hermes_cfo_loop_shadow.py
- current behavior: Blocked from primary mode and high-risk approval categories.
- approval required: True
- approval boundary shown: True
- blocked correctly: True
- risk level: high
- recommendation: No autonomous spend path should remain in generic router.

## live trading
- function: Evidence gate plus approval/risk boundaries
- file: lib/telegram_router.py / hermes_command_router/router.py / lib/hermes_approval_queue.py
- current behavior: Fake trading claims blocked; live trading remains explicit high risk.
- approval required: True
- approval boundary shown: True
- blocked correctly: True
- risk level: high
- recommendation: Keep paper/demo separated from live trading policy.

## Supabase writes
- function: Learning loop lesson approval; selected migration/backfill scripts outside live Telegram
- file: lib/hermes_learning_loop.py
- current behavior: Possible only on approved lesson paths; audit scripts must not trigger.
- approval required: True
- approval boundary shown: True
- blocked correctly: True
- risk level: high
- recommendation: Treat hermes_memory_v2 writes as separate maintenance operations.

## external network/model calls
- function: TelegramRouter conversational fallback, command router model router, provider checks
- file: lib/telegram_router.py / hermes_command_router/router.py / lib/hermes_provider_policy.py
- current behavior: Still possible in non-plain/router/model-backed paths.
- approval required: False
- approval boundary shown: False
- blocked correctly: False
- risk level: medium
- recommendation: Prefer local deterministic paths for audits and safety-sensitive commands.
