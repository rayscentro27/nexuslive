# Autonomous Demo Trading Enablement

- Enabled safe autonomous demo-learning surface via snapshot + visualization layers while keeping hard live-trading blocks intact.
- Preserved hard safety flags:
  - `LIVE_TRADING=false`
  - `TRADING_LIVE_EXECUTION_ENABLED=false`
  - `NEXUS_AUTO_TRADING=false`
- Added simulation telemetry visibility in `central_operational_snapshot`:
  - autonomous/sim mode flags
  - journal/outcome counts
  - win/loss distribution
  - simulated net PnL
  - simulated max drawdown
- Added bounded paper-learning visualization in Workforce + Trading dashboards.

## Safeguards surfaced
- max-concurrency/drawdown safety is represented via warnings and drawdown telemetry in snapshot.
- emergency disable remains controlled by environment/runtime switches and existing service controls.
