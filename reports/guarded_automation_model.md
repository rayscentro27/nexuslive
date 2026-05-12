# Guarded Automation Model
**Date:** 2026-05-12  
**Mode:** Architecture design — future state, TRADING_LIVE_EXECUTION_ENABLED=false (stays false until criteria met)

---

## The Core Distinction

**WRONG model:** "AI decides to trade → AI executes"  
**RIGHT model:** "Human approves a boundary → AI executes within that boundary"

The difference is who sets the rules. The human always sets the rules. The AI executes within them.

---

## Approval Layers (What Humans Approve)

### Layer 1 — Strategy Approval
Before any strategy can execute (paper or live), a human must review and approve:

```
Strategy Approval Checklist:
[ ] Strategy name and description reviewed
[ ] Market(s) approved (which pairs/instruments)
[ ] Timeframe(s) approved
[ ] Session restrictions approved
[ ] Entry logic reviewed and understood
[ ] Exit logic reviewed (SL/TP/trailing)
[ ] Risk parameters approved (see Layer 2)
[ ] Backtest results reviewed (30+ trades minimum)
[ ] Paper trading results reviewed (30+ trades minimum)
Signed off by: Raymond Davis
Date:
```

### Layer 2 — Risk Model Approval
```
Risk Parameter Approval:
[ ] Max risk per trade: ___% approved
[ ] Max daily loss limit: ___% approved
[ ] Max weekly drawdown: ___% approved
[ ] Max open positions: ___ approved
[ ] Leverage limit: ___:1 approved
[ ] Approved markets: ___________ approved
[ ] Approved sessions: ___________ approved
[ ] Correlated exposure limit: ___% approved
[ ] Consecutive loss halt: ___ approved
Signed off by: Raymond Davis
Date:
```

### Layer 3 — Automation Permission
```
Automation Permission:
[ ] Paper trading stage: PASS (minimum criteria met)
[ ] Circuit breakers reviewed and tested
[ ] Hermes monitoring active
[ ] Risk engine validated against paper data
[ ] This strategy is authorized for guarded automation

Automation scope (check all that apply):
[ ] Entry execution within approved risk limits
[ ] Exit execution (TP/SL only)
[ ] Trailing stop management
[ ] Position sizing (within approved formula)

NOT authorized (cannot be enabled without new sign-off):
[ ] Adding leverage beyond approved limit
[ ] Expanding position sizes beyond formula
[ ] Opening positions during news events
[ ] Executing outside approved sessions
[ ] Overriding circuit breakers

Signed off by: Raymond Davis
Date:
```

---

## Execution Boundary Contract

Once a strategy is approved, the automation operates within a strict boundary contract:

```python
class ExecutionBoundary:
    strategy_id: str
    approved_by: str
    approved_at: datetime
    
    # Markets
    approved_markets: list[str]         # ["EURUSD", "GBPUSD"]
    approved_sessions: list[str]        # ["london", "ny_open"]
    
    # Risk limits
    max_risk_pct_per_trade: float       # 1.0
    max_daily_loss_pct: float           # 2.0
    max_weekly_dd_pct: float            # 5.0
    max_concurrent_positions: int       # 3
    max_leverage: int                   # 30
    
    # Execution scope
    can_enter: bool                     # approved for entries
    can_exit_tp_sl: bool               # approved for TP/SL exits
    can_trail: bool                     # approved for trailing stops
    
    # Hard limits (never overrideable)
    never_trade_news: bool = True       # hardcoded True
    never_exceed_leverage: bool = True  # hardcoded True
    circuit_breakers_override_all: bool = True  # hardcoded True
```

The execution engine checks this contract before every action. It cannot be modified at runtime — only through a new human approval cycle.

---

## Transition Roadmap

```
Phase 1 (NOW): Research + Backtesting
- Strategy development
- Historical backtesting
- Risk parameter modeling
- No execution

Phase 2 (PAPER): Paper Trading
- All risk engine layers active
- All circuit breakers active
- Same code path as future live execution
- Validates strategy AND risk engine simultaneously
- 30+ trades required per strategy

Phase 3 (REVIEW): Human Approval
- Complete trade journal reviewed
- Performance vs backtest reviewed
- Risk parameters signed off
- Circuit breakers confirmed working
- Automation permissions granted per checklist

Phase 4 (GUARDED): Live Execution with Boundaries
- TRADING_LIVE_EXECUTION_ENABLED=true (operator sets this)
- Only strategies with Phase 3 approval can run
- Risk engine enforces all approved boundaries
- Hermes monitors and reports
- Any parameter change requires new approval cycle

Phase 5 (OPTIMIZED): Adaptive within Boundaries
- Hermes recommends parameter adjustments
- Each recommendation reviewed before applying
- Boundaries can be tightened any time (no approval needed)
- Boundaries can only be loosened with new approval cycle
```

---

## What Automation Can and Cannot Do

### CAN do (within approved boundaries)
- Execute entries when signal quality meets threshold
- Place TP/SL orders immediately on entry
- Manage trailing stops per approved formula
- Size positions per approved risk formula
- Skip trades when risk engine blocks
- Pause strategy on consecutive loss threshold
- Alert Hermes on circuit breaker events

### CANNOT do (hardcoded, cannot be configured away)
- Add leverage beyond approved limit
- Execute during news blackout
- Execute outside approved sessions
- Override circuit breakers
- Withdraw funds
- Transfer between accounts
- Modify risk parameters at runtime
- Execute unapproved strategies
- Increase position sizes mid-trade
- Enable itself after circuit breaker fires (human reset required)

---

## Circuit Breaker Override Protocol

If a circuit breaker fires during live execution:
1. All open positions maintained (no panic close — markets can be volatile)
2. No new entries accepted
3. Hermes sends immediate Telegram alert
4. Operator reviews the event
5. Operator manually resets after review
6. Hermes logs resolution with reason

No automated circuit breaker reset. Ever.

---

## Monitoring and Accountability

Every automated action is logged:
- What was executed
- Which boundary it operated within
- Risk score at time of execution
- Which circuit breaker checks passed
- Hermes review timestamp

Weekly accountability review:
- Did automation operate within boundaries? (yes/no)
- Any boundary violations attempted? (logged)
- Circuit breaker events this week?
- Recommendation: tighten, maintain, or expand boundaries?
- Only operator can expand. Hermes can only recommend.
