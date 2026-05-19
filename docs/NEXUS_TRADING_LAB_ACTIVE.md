# Nexus Trading Research Lab — ACTIVE

**Status:** ACTIVE — Paper Trading Research Only  
**Last Updated:** 2026-05-19  
**Safety Mode:** PAPER ONLY | NO LIVE TRADING | NO BROKER | NO REAL MONEY

---

## HARD SAFETY RULES — NON-NEGOTIABLE

```
LIVE_TRADING = false
REAL_MONEY_TRADING = false
TRADING_LIVE_EXECUTION_ENABLED = false
BROKER_CONNECTION = false
API_TRADING_KEYS = none
AUTO_ORDER_EXECUTION = blocked
MINIMUM_PAPER_PERIOD = 6 months before any live consideration
```

All work in this lab is for research, simulation, education, and framework development.  
No live execution for minimum 6 months of verified paper performance.

---

## PAPER TRADING JOURNAL SYSTEM

### Database Schema

```sql
-- Applied to Supabase (paper trading journal — no live data)
CREATE TABLE IF NOT EXISTS paper_trade_journal (
  id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  strategy_id         TEXT NOT NULL,           -- e.g., 'forex_london_breakout_v1'
  strategy_version    TEXT NOT NULL DEFAULT '1.0',
  market              TEXT NOT NULL,           -- e.g., 'GBP/USD', 'BTC/USD'
  asset_class         TEXT NOT NULL
    CHECK (asset_class IN ('forex','crypto','options','equities')),
  session             TEXT,                    -- 'london', 'ny', 'asia', 'overlap'
  timeframe           TEXT NOT NULL,           -- '15m', '1h', '4h', 'daily'
  direction           TEXT NOT NULL
    CHECK (direction IN ('long','short','neutral')),

  -- Entry
  entry_date          DATE NOT NULL,
  entry_time          TIME,
  entry_price         DECIMAL(18,8) NOT NULL,
  entry_reason        TEXT,

  -- Risk
  stop_loss           DECIMAL(18,8) NOT NULL,
  take_profit_1       DECIMAL(18,8),
  take_profit_2       DECIMAL(18,8),
  risk_pct            DECIMAL(5,4) DEFAULT 0.01,  -- 1% = 0.01
  position_size       DECIMAL(18,4),
  risk_usd            DECIMAL(12,2),

  -- Exit
  exit_date           DATE,
  exit_time           TIME,
  exit_price          DECIMAL(18,8),
  exit_reason         TEXT,

  -- Results
  result_r            DECIMAL(8,4),            -- result in R (1R = risk)
  result_pct          DECIMAL(8,4),
  paper_pnl_usd       DECIMAL(12,2),
  outcome             TEXT
    CHECK (outcome IN ('win','loss','breakeven','open','missed','skipped')),

  -- Context
  atr_at_entry        DECIMAL(12,6),
  vix_at_entry        DECIMAL(8,4),
  market_condition    TEXT,
  news_nearby         BOOLEAN DEFAULT FALSE,
  setup_quality       INTEGER CHECK (setup_quality BETWEEN 1 AND 5),
  followed_rules      BOOLEAN DEFAULT TRUE,

  notes               TEXT,
  screenshot_ref      TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON paper_trade_journal(strategy_id, entry_date DESC);
CREATE INDEX ON paper_trade_journal(asset_class, outcome);
```

### Position Sizing Calculator

```python
def calculate_paper_position_size(account_balance: float, risk_pct: float,
                                   entry: float, stop_loss: float) -> dict:
    """
    Paper trading position size. No live orders.
    Returns size + risk breakdown for journal entry.
    """
    risk_amount = account_balance * risk_pct
    distance = abs(entry - stop_loss)
    if distance == 0:
        raise ValueError("Stop loss cannot equal entry price")
    position_size = risk_amount / distance
    return {
        "account_balance": account_balance,
        "risk_pct": risk_pct,
        "risk_usd": round(risk_amount, 2),
        "distance": round(distance, 5),
        "position_size": round(position_size, 2),
        "note": "PAPER TRADE ONLY — no live execution"
    }

# Example: $10,000 paper account, 1% risk, GBP/USD entry 1.2500, stop 1.2470
# risk_amount = $100
# distance = 30 pips = 0.0030
# position_size = $100 / 0.0030 = 33,333 units (0.33 lots)
```

---

## RISK MANAGEMENT SYSTEM

### Hard Risk Limits

| Rule | Limit | Action on Breach |
|------|-------|------------------|
| Risk per trade (standard) | 1% of paper account | Reduce size or skip |
| Risk per trade (volatile market) | 0.5% of paper account | For crypto/options |
| Max daily paper loss | 3% of paper account | Stop paper trading for the day |
| Max weekly drawdown | 6% of paper account | Review strategy, reduce size |
| Max monthly drawdown | 12% of paper account | Full strategy pause + audit |
| Consecutive paper losses | 4 in a row | Pause 5 sessions |
| Correlated paper positions | 2 max open simultaneously | Never hold 3 correlated assets |
| News window | ±30 min of major data | No entries near high-impact news |

### Drawdown Recovery Protocol

| Drawdown Level | Protocol |
|----------------|----------|
| 3–5% | Monitor — note market conditions, review last 5 trades |
| 5–8% | Reduce paper position size by 50%, review last 10 trades |
| 8–12% | Stop new paper trades, full audit of last 20 trades |
| 12%+ | Full strategy pause — return to simulation mode, no paper entries |

---

## DRAWDOWN TRACKING SYSTEM

```python
class DrawdownTracker:
    """Track paper account peak, current, and drawdown status."""
    
    def __init__(self, starting_balance: float):
        self.starting_balance = starting_balance
        self.peak_balance = starting_balance
        self.current_balance = starting_balance
        self.drawdown_log = []
    
    def update(self, current_balance: float, date: str):
        self.current_balance = current_balance
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        drawdown_pct = (self.peak_balance - current_balance) / self.peak_balance
        self.drawdown_log.append({
            "date": date,
            "balance": current_balance,
            "peak": self.peak_balance,
            "drawdown_pct": round(drawdown_pct * 100, 2),
            "status": self._status(drawdown_pct),
        })
        return drawdown_pct
    
    def _status(self, pct: float) -> str:
        if pct < 0.03: return "normal"
        if pct < 0.05: return "monitor"
        if pct < 0.08: return "reduce_size"
        if pct < 0.12: return "pause_review"
        return "full_pause"
    
    def current_drawdown_pct(self) -> float:
        return (self.peak_balance - self.current_balance) / self.peak_balance * 100
```

---

## WIN/LOSS EXPECTANCY + RR TRACKING

```python
from statistics import mean, stdev
from typing import List

def calculate_expectancy(win_rate: float, avg_win_r: float,
                          avg_loss_r: float = 1.0) -> dict:
    """
    Core expectancy formula for paper trading analysis.
    Target: > 0.5R per trade for viable strategy.
    """
    loss_rate = 1 - win_rate
    expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)
    return {
        "expectancy_r": round(expectancy, 4),
        "interpretation": "viable" if expectancy > 0.5 else "below target",
        "win_rate": win_rate,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
    }

def profit_factor(gross_wins: float, gross_losses: float) -> float:
    """Target: > 1.5. Below 1.0 = net losing system."""
    if gross_losses == 0:
        return float('inf')
    return round(gross_wins / gross_losses, 3)

def simplified_sharpe(returns: List[float], risk_free: float = 0) -> float:
    """Simplified Sharpe for paper trade return list. Target: > 1.0."""
    if len(returns) < 2:
        return 0.0
    avg = mean(returns) - risk_free
    std = stdev(returns)
    return round(avg / std, 3) if std else 0.0

def max_consecutive_losses(outcomes: List[str]) -> int:
    max_streak = current_streak = 0
    for o in outcomes:
        if o == 'loss':
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    return max_streak

# Evaluation targets (minimum 30 trades)
TARGETS = {
    "expectancy_r": 0.5,     # > 0.5R per trade
    "profit_factor": 1.5,    # > 1.5
    "sharpe": 1.0,           # > 1.0 (annualized)
    "win_rate": 0.45,        # > 45% minimum
    "max_drawdown_pct": 12,  # < 12% of paper account
}
```

---

## ACTIVE STRATEGIES — PAPER RESEARCH

### FOREX — Strategy 1: London Breakout

**ID:** `forex_london_breakout_v1`  
**Paper market:** GBP/USD, EUR/USD  
**Session:** London open — 3:00 AM to 5:00 AM EST  
**Timeframe:** 15-minute chart  

**Setup rules:**
1. Pre-session range: identify high and low from 7:00 PM to 2:00 AM EST
2. ATR(14) must be above 7-day average ATR (no low-volatility entry)
3. Range height must be > 15 pips (too narrow = unreliable breakout)
4. No entries on NFP, FOMC, or central bank announcement days

**Entry rules:**
- Long: 15M candle closes ABOVE range high → enter next candle open
- Short: 15M candle closes BELOW range low → enter next candle open
- Maximum 1 paper trade per day (first valid setup only)
- No entries after 6:00 AM EST

**Exit rules:**
- TP1: 1× range height (exit 50% of paper position)
- TP2: 1.5× range height (exit remaining 50%)
- SL: Opposite side of pre-session range
- Breakeven: Move SL to entry when TP1 hit

**Paper tracking targets:** Win rate >50% | Expectancy >0.5R | Min 30 trades

---

### FOREX — Strategy 2: Trend Pullback (EMA Retest)

**ID:** `forex_trend_pullback_v1`  
**Paper market:** EUR/USD, USD/JPY, GBP/USD  
**Session:** London + NY overlap — 8:00 AM to 2:00 PM EST  
**Timeframe:** 1H trend context, 15M entry  

**Entry rules (long):**
1. 1H: EMA 20 above EMA 50, both sloping up
2. Price pulls back to EMA 20 zone on 15M
3. 15M RSI reaches 40–55 (pullback, not exhaustion)
4. 15M candle closes bullish from EMA 20 area
5. Enter on next candle open

**Exit rules:**
- TP: Previous 1H swing high or 2.5× ATR from entry
- SL: 1× ATR below entry candle low (long) / above (short)
- Breakeven: Move SL at 1:1

**Paper targets:** Win rate >50% | RR minimum 1:2 | Max 2 paper trades/day

---

### CRYPTO — Strategy 1: BTC/ETH Trend Continuation

**ID:** `crypto_trend_continuation_v1`  
**Paper market:** BTC/USD, ETH/USD (price data via CoinGecko free API)  
**Timeframe:** 4H chart  

**Entry rules:**
1. EMA 20 > EMA 50 > EMA 200 (all aligned, all sloping)
2. MACD(12,26,9): line crosses above signal (long)
3. Volume bar > 20-period volume moving average
4. Price above EMA 20 for longs, below for shorts

**Exit rules:**
- TP1: 3× ATR from entry (scale 50% out)
- TP2: Previous swing high/low
- SL: Below EMA 50 for longs / above for shorts
- Time stop: Close after 10 candles if no movement

**Paper targets:** Expectancy >0.5R | Min 30 trades before evaluation

---

### CRYPTO — Strategy 2: Volatility Breakout (Bollinger Squeeze)

**ID:** `crypto_volatility_breakout_v1`  
**Paper market:** BTC/USD, ETH/USD, SOL/USD (price tracking only)  
**Timeframe:** 1H chart  

**Setup (squeeze detection):**
1. Bollinger Bands(20, 2.0) width at 30-day minimum
2. ATR(14) below 20-period ATR average
3. Price consolidating inside bands for 4+ candles

**Entry rules:**
1. Candle closes OUTSIDE the Bollinger Band
2. Volume on that candle > 2× 20-period average volume
3. Enter at open of NEXT candle
4. Do not chase if price has moved > 0.5× ATR past breakout candle close

**Risk per paper trade:** 0.5% (higher volatility asset)  
**Max paper trades/week:** 3

---

### OPTIONS — Strategy 1: SPY Trend Continuation

**ID:** `options_spy_trend_v1`  
**Paper tracking:** SPY (no real contracts, data via Yahoo Finance)  
**Hypothetical paper position:** 30-delta call/put, 30–45 DTE

**Setup:**
1. SPY above/below 50-day SMA
2. VIX below 20 (lower IV = cheaper theoretical premium)
3. 3-day pullback to 20-day SMA
4. Entry day: price bounces from SMA with volume

**Paper tracking method:**
- Record: strike, expiry, theoretical premium (options calculator)
- Track: daily theoretical P&L via delta × price move approximation
- No real contracts purchased or simulated brokerage

**Paper exit rules:**
- TP: 50% of theoretical max profit
- SL: 200% of theoretical premium (lose 2× the premium)
- Time stop: Close at 21 DTE

---

### OPTIONS — Strategy 2: QQQ Momentum Breakout

**ID:** `options_qqq_momentum_v1`  
**Paper tracking:** QQQ (data via Yahoo Finance / TradingView)  

**Setup:**
1. QQQ breaks 52-week high or major resistance
2. Weekly RSI(14) between 55–70
3. Breakout confirmed with 1.5× average volume

**Paper position (theoretical):** ATM call, 45–60 DTE, 1% paper account max  
**Exit:** 100% gain → exit half; 50% loss → close; 30 DTE → close if not profitable

---

## DAILY TRADING REPORT FORMAT

```
═══════════════════════════════════════════════════════
NEXUS PAPER TRADING DAILY REPORT — [YYYY-MM-DD]
═══════════════════════════════════════════════════════
SESSION: [London / NY / Both / No setup]
PAPER ACCOUNT VALUE: $[X,XXX.XX]
DAILY P&L: $[+/-X.XX] ([+/-]X.X%)
SAFETY STATUS: PAPER ONLY | NO LIVE TRADES | NO BROKER

TODAY'S PAPER TRADES:
Strategy        Market    Dir    Entry    Exit     R
──────────────────────────────────────────────────────
[strategy_id]   GBP/USD   Long   1.2500   1.2540   +1.3R
[or: No valid setups today]

RUNNING TOTALS (Last 30 Days):
Total paper trades:     [X]
Win rate:               [XX]%  (Target: >50%)
Total R gained:         [+/-X.X]R
Expectancy per trade:   [X.X]R  (Target: >0.5R)
Profit factor:          [X.X]  (Target: >1.5)
Max drawdown:           [X.X]%  (Limit: 12%)
Current streak:         [X wins / X losses]
Consecutive loss max:   [X]  (Limit: 4)

STRATEGY PERFORMANCE:
forex_london_breakout_v1:       [W]-[L]  Win rate: [X]%
forex_trend_pullback_v1:        [W]-[L]  Win rate: [X]%
crypto_trend_continuation_v1:   [W]-[L]  Win rate: [X]%
crypto_volatility_breakout_v1:  [W]-[L]  Win rate: [X]%

OBSERVATIONS:
+ [1 thing that worked today]
- [1 thing to review or improve]

NEWS/EVENTS TO WATCH TOMORROW:
- [Economic calendar items that affect paper setups]

NEXT SESSION SETUPS TO MONITOR:
- [Specific setup conditions forming]

LIVE TRADING STATUS: NOT YET ELIGIBLE
Required: 6 months verified paper performance across all strategies
Current paper period: [X] weeks of [26 weeks required]
═══════════════════════════════════════════════════════
```

---

## WEEKLY PERFORMANCE REVIEW FORMAT

```
═══════════════════════════════════════════════════════
NEXUS PAPER TRADING WEEKLY REVIEW
WEEK OF: [Mon YYYY-MM-DD to Fri YYYY-MM-DD]
═══════════════════════════════════════════════════════
PAPER ACCOUNT VALUE: $[X,XXX.XX]
WEEK START VALUE:    $[X,XXX.XX]
WEEK P&L:            $[+/-X.XX] ([+/-]X.X%)

TRADES THIS WEEK: [X]
WIN RATE: [XX]%        (Target: >50%)
TOTAL R: [+/-X.X]R    (Target: >0.5R/week)
PROFIT FACTOR: [X.X]  (Target: >1.5)
SHARPE (weekly): [X.X]  (Target: >1.0)
MAX SINGLE LOSS: [X.X]R
MAX DRAWDOWN: [X.X]%   (Limit: 12%)

RULE ADHERENCE: [X]/[X] paper trades followed all rules

STRATEGY BREAKDOWN:
──────────────────────────────────────────────────────
Strategy                  Trades  Wins  R    WR%
──────────────────────────────────────────────────────
forex_london_breakout_v1  [X]     [X]   [X]  [X]%
forex_trend_pullback_v1   [X]     [X]   [X]  [X]%
crypto_trend_cont_v1      [X]     [X]   [X]  [X]%
crypto_vol_breakout_v1    [X]     [X]   [X]  [X]%
options_spy_trend_v1      [X]     [X]   [X]  [X]%
options_qqq_momentum_v1   [X]     [X]   [X]  [X]%

IMPROVEMENTS NEEDED:
1. [Specific rule or setup issue]
2. [Second improvement area]

NEXT WEEK FOCUS:
- [Setup priority]
- [Market to watch]
- [Rule reinforcement]

LIVE TRADING ELIGIBILITY CHECK:
Required: 30+ trades per strategy + 6 months + no rule violations
Status: [X weeks into paper period — X% complete]
═══════════════════════════════════════════════════════
```

---

## TRADING DASHBOARD PLANNING (Future nexuslive Integration)

When paper period is complete and a dashboard is added:

1. **Strategy Status Cards** — win rate + last 10 trades per strategy
2. **Equity Curve Chart** — paper account cumulative R over time
3. **Streak Tracker** — current win/loss streak indicator
4. **Next Setup Radar** — real-time condition checklist per strategy
5. **Risk Dashboard** — daily/weekly drawdown vs. limits
6. **Trade Log Table** — searchable, filterable paper trade history
7. **PAPER ONLY watermark** — on every chart and panel

**Tech stack:** nexuslive (React + Supabase) + `paper_trade_journal` table + free market data APIs

---

## LIVE TRADING ELIGIBILITY CRITERIA

Before any consideration of live trading:

| Criterion | Requirement | Current Status |
|-----------|-------------|----------------|
| Paper period | 6+ months continuous | Starting |
| Minimum sample | 30+ trades per strategy | 0/30 each |
| Win rate | >50% per strategy | TBD |
| Expectancy | >0.5R per strategy | TBD |
| Max drawdown | <12% of paper account | TBD |
| Rule adherence | >95% trades followed rules | TBD |
| Consecutive loss max | <5 in row per strategy | TBD |
| Ray approval | Explicit go/no-go decision | Required |

**Current status: 🔴 NOT ELIGIBLE — Paper research period just beginning**
