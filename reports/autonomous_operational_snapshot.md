# Autonomous Operational Snapshot

- Central snapshot expanded to support autonomous learning operations:
  - `paper_trading` block with simulation flags, PnL, drawdown, outcomes, and recent rows
  - `strategy_rankings` block with top active strategy signals
  - `business_experiments` block with status/active counts and recent rows
- Existing operational sections preserved (ingestion, providers, workforce, scheduler, warnings/errors).
- Endpoint remains read-only and suitable as shared source for Workforce Office, Hermes, and admin views.
