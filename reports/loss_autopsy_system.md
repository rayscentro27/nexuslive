# Loss Autopsy System

Implemented in `lib/adaptive_trading_intelligence.py` via `record_loss_autopsy()`.

Autopsy fields include:
- strategy used
- market state
- entry and confidence rationale
- failure and missed condition
- fakeout/volatility/timing/behavioral issues
- drawdown impact
- avoidability decision
- lesson learned

Autopsies persist to `state/loss_autopsies.json` for failure-memory continuity.
