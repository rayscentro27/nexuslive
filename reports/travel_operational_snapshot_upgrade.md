# Travel Operational Snapshot Upgrade

- Central snapshot (`lib/central_operational_snapshot.py`) expanded to include `paper_trading` telemetry:
  - simulation flags
  - recent journal/outcome counts
  - win/loss counts
  - simulated win rate
  - net simulated PnL
  - max drawdown
  - latest journal/outcome rows
- Existing operational sections preserved (ingestion, providers, workforce, research load, scheduler, warnings/errors).
- Snapshot remains read-only and admin-guarded via `/api/admin/ai-ops/status`.
