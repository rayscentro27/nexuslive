# Autonomous Paper Trading Enablement

- Kept hard safety posture intact: `LIVE_TRADING=false`, `TRADING_LIVE_EXECUTION_ENABLED=false`, `NEXUS_AUTO_TRADING=false`.
- Added simulation-mode visibility in centralized snapshot (`paper_trading` block) with flags:
  - `AUTONOMOUS_PAPER_TRADING`
  - `SIMULATED_TRADING_ENABLED`
  - `TRADING_SIMULATION_MODE`
- Added simulated performance telemetry surfacing:
  - recent journal entries/outcomes
  - win/loss counts and win rate
  - net simulated PnL
  - max simulated drawdown
- Workforce and Trading visual layers now consume these metrics for real-time paper-trading readiness cues.
