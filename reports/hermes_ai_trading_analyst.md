# Hermes AI Trading Analyst — Role + Responsibilities
**Date:** 2026-05-12  
**Mode:** Design — paper trading only, TRADING_LIVE_EXECUTION_ENABLED=false

---

## Role Definition

Hermes is the AI Chief of Staff for Nexus. In the trading context, Hermes acts as the AI analyst layer: reading strategy results, synthesizing performance data, flagging risks, and recommending actions. Hermes never executes trades. Hermes never modifies risk parameters. Hermes reads, analyzes, and reports.

**What Hermes IS in trading context:**
- Performance analyst: reads trade journal, surfaces patterns
- Risk monitor: tracks circuit breakers, drawdown proximity, streak health
- Strategy commentator: daily/weekly digest on each strategy's condition
- Recommendation engine: suggests parameter reviews, session adjustments
- Alert dispatcher: Telegram + email for circuit breaker events, threshold breaches

**What Hermes IS NOT:**
- Not an execution engine
- Not a signal generator
- Not a risk parameter setter (can only recommend, not apply)
- Not able to approve strategies for live execution
- Not able to reset circuit breakers

---

## Hermes Trading Analyst Commands (Telegram)

```
/trading status       — current paper account, open positions, today's P&L
/trading strategies   — leaderboard: all strategies ranked this week
/trading risk         — risk engine state, circuit breakers, proximity to limits
/trading journal      — last 10 trades with entry/exit/pips/reason
/trading sessions     — win rate by session this week
/trading review [strategy_id] — deep dive on specific strategy
/trading alerts       — pending alerts, unresolved circuit breaker events
```

---

## Daily Trading Digest (Hermes Auto-Report)

Sent every trading day at market close (after NY session):

```
📊 NEXUS TRADING DAILY — [date]

PAPER ACCOUNT
Balance: $10,847  Today: +$347 (+0.32%)
High-water mark: $11,102  Drawdown from HWM: 2.3%

STRATEGIES TODAY
🥇 London Breakout v2.1  +$287  3 trades  67% WR
🥈 NY Momentum           +$60   2 trades  50% WR
❌ SPY Continuation       -$0    0 trades  (session filter blocked)

RISK ENGINE
Circuit breakers: None active
Daily risk used: 0.9% of 2.0% limit
Weekly drawdown: 1.2% of 5.0% limit
Open positions: 0 (closed for day)

HERMES TAKE
London Breakout has won 4 of last 5 sessions —
edge appears stable in London open volatility.
NY Momentum's 50% WR over 8 trades is below
the 60% backtest baseline. Recommend reviewing
NY session entry conditions before trade 15.

Tomorrow: London open in 14h 22m
```

---

## Weekly Strategy Review (Hermes)

Sent every Monday before market open:

```
📋 NEXUS WEEKLY REVIEW — Week of [date]

LEADERBOARD SHIFT
↑ London Breakout  #1 (was #2)  +4.2%  71% WR  PF: 2.3x
→ SPY Continuation #2 (stable)  +1.8%  61% WR  PF: 1.6x
↓ NY Momentum      #3 (was #1)  -0.4%  44% WR  PF: 0.9x

EDGE HEALTH
London Breakout:  STABLE  (win rate within 8% of backtest)
SPY Continuation: STABLE  (win rate within 5% of backtest)
NY Momentum:      WARNING (win rate 16% below backtest — exceeded -15% threshold)

ACTION ITEM
NY Momentum win rate has deteriorated past the -15% threshold.
Strategy has been paused automatically. Recommend:
1. Review last 10 NY Momentum trades in journal
2. Check if edge is session-specific or signal quality
3. Either adjust entry parameters or remove from rotation
Your decision required before strategy resumes.

CIRCUIT BREAKER LOG
No circuit breakers fired this week.

PROGRESS TO LIVE
London Breakout: 34 trades  ✅ 30+ minimum met
SPY Continuation: 22 trades  🔄 8 more needed
NY Momentum: 18 trades  ❌ paused — resolve edge deterioration first
```

---

## Circuit Breaker Alert Format

Sent immediately when any circuit breaker fires:

```
🚨 CIRCUIT BREAKER FIRED — [timestamp]

Trigger: Daily loss limit exceeded
Value: -2.3% (limit: 2.0%)
Strategy: London Breakout v2.1
Trade: EUR/USD SHORT, -$230

ACTION TAKEN:
✅ All new entries blocked
✅ Open positions maintained (2 positions held)
✅ No automatic closes

WHAT YOU NEED TO DO:
Review the journal entry for this session.
If satisfied, use /trading reset_daily to restore.
No automated reset will occur.

— Hermes
```

---

## Hermes Strategy Analysis Template

When `/trading review [strategy_id]` is called:

```python
class StrategyAnalysis:
    strategy_id: str
    analysis_date: datetime
    
    # Performance summary
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    max_drawdown_pct: float
    sharpe_ratio: float
    
    # Backtest comparison
    backtest_win_rate: float
    live_vs_backtest_delta: float       # positive = outperforming
    edge_health: str                    # "stable" | "degrading" | "critical"
    
    # Session breakdown
    best_session: str
    worst_session: str
    session_win_rates: dict[str, float]
    
    # Hermes recommendation
    recommendation: str                 # "maintain" | "review_params" | "pause" | "retire"
    reasoning: str
    specific_actions: list[str]
```

---

## AI Signal Analysis (Future Phase 5)

In Phase 5 (Optimized — not current phase), Hermes may use LLM analysis to evaluate:
- Multi-timeframe confluence for signal quality scoring
- Market regime detection (trending vs ranging)
- Correlation analysis across open positions
- News sentiment impact on strategy performance

**Current phase (Phase 1-2):** Hermes reads existing data only. No LLM analysis of market conditions. No signal generation.

---

## Hermes Knowledge Integration

Trading performance data feeds into the Nexus knowledge system:
- Weekly performance report → NotebookLM digest queue
- Strategy approval checklists → stored as knowledge documents
- Circuit breaker events → logged for pattern analysis

Hermes can answer questions like:
- "What was our best performing session last month?"
- "How many circuit breaker events has London Breakout triggered?"
- "What's the trend on win rate over the last 30 trades?"

These are answered from the trade journal database, not LLM hallucination.

---

## Data Access (Read-Only)

Hermes has read access to:
- `paper_trades` table (all columns)
- `risk_checks` table (all columns)
- `circuit_breaker_events` table (all columns)
- `strategy_registry` (strategy definitions)
- `execution_boundaries` (approved parameters)

Hermes has NO write access to:
- `execution_boundaries` (cannot change approved parameters)
- `strategy_registry` (cannot enable/disable strategies)
- Circuit breaker state (cannot reset)
- Live trading configuration (cannot touch)
