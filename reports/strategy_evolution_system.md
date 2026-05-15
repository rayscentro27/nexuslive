# Strategy Evolution System

- Strategy evolution readiness improved by centralizing simulation outcomes and ranking context.
- Added snapshot fields for:
  - strategy rankings (`strategy_rankings.top_active`)
  - confidence-oriented active strategy ordering
  - paper-trading win/loss and drawdown context
- Trading dashboard now reflects evolution inputs (outcomes, win rate, drawdown, net simulated PnL).
- Workforce trading lane now reflects strategy-journal activity to indicate active learning cycles.

## Current limits
- Core strategy mutation remains bounded and review-oriented; no unbounded self-modifying execution path introduced.
