# Task Guardrails

Date: 2026-05-15

Approval gating implemented in `lib/ai_task_dispatch.py` (`requires_manual_approval`).

Manual approval required for:
- production deploys
- destructive repo operations
- database schema deletes
- real-money trading changes
- env modifications
- payment integrations

Autonomous-safe tasks allowed:
- reports
- analysis
- testing
- UI drafts
- safe feature branch implementation
- demo improvements
- simulations

Safety posture preserved:
- `NEXUS_DRY_RUN=true`
- `REAL_MONEY_TRADING=false`
- `LIVE_TRADING=false`
- `TRADING_LIVE_EXECUTION_ENABLED=false`
