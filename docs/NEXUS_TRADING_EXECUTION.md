# Nexus Trading Research Lab — Execution

**Created:** 2026-05-19  
**Status:** ACTIVE — paper-only, gate approved  
**Approval ID:** `674ac406-b3e8-446a-aa3d-c31bd61c83a9` ← APPROVED

---

## HARD SAFETY RULES

```
LIVE_TRADING = false
REAL_MONEY_TRADING = false
TRADING_LIVE_EXECUTION_ENABLED = false
BROKER_CONNECTION = false
API_TRADING_KEYS = none
AUTO_ORDER_EXECUTION = blocked
```

All work in this document is for research, paper simulation, and educational
framework development only. No live execution for minimum 6 months of verified
paper performance.

---

## PAPER TRADING JOURNAL SCHEMA

```sql
-- ── paper_trade_journal ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paper_trade_journal (
  id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  strategy_id         TEXT NOT NULL,           -- e.g., 'forex_london_breakout_v1'
  strategy_version    TEXT NOT NULL DEFAULT '1.0',
  market              TEXT NOT NULL,           -- e.g., 'GBP/USD', 'BTC/USD', 'SPY'
  asset_class         TEXT NOT NULL            -- 'forex', 'crypto', 'options', 'equities'
    CHECK (asset_class IN ('forex','crypto','options','equities')),
  session             TEXT,                    -- 'london', 'ny', 'asia', 'overlap'
  timeframe           TEXT NOT NULL,           -- '15m', '1h', '4h', 'daily'
  direction           TEXT NOT NULL
    CHECK (direction IN ('long','short','neutral')),
  
  -- Entry
  entry_date          DATE NOT NULL,
  entry_time          TIME,
  entry_price         DECIMAL(18,8) NOT NULL,
  entry_reason        TEXT,                    -- specific setup description
  
  -- Risk parameters
  stop_loss           DECIMAL(18,8) NOT NULL,
  take_profit_1       DECIMAL(18,8),
  take_profit_2       DECIMAL(18,8),
  risk_pct            DECIMAL(5,4) DEFAULT 0.01,  -- 1% = 0.01
  position_size       DECIMAL(18,4),
  risk_usd            DECIMAL(12,2),           -- paper USD risk amount
  
  -- Exit
  exit_date           DATE,
  exit_time           TIME,
  exit_price          DECIMAL(18,8),
  exit_reason         TEXT,                    -- TP hit, SL hit, manual, time
  
  -- Results
  result_r            DECIMAL(8,4),            -- result in R (1R = risk amount)
  result_pct          DECIMAL(8,4),            -- % return on position
  paper_pnl_usd       DECIMAL(12,2),           -- paper P&L in USD
  outcome             TEXT
    CHECK (outcome IN ('win','loss','breakeven','open','missed','skipped')),
  
  -- Context
  atr_at_entry        DECIMAL(12,6),
  vix_at_entry        DECIMAL(8,4),            -- for options/equities
  market_condition    TEXT,                    -- 'trending','ranging','volatile'
  news_nearby         BOOLEAN DEFAULT FALSE,
  setup_quality       INTEGER CHECK (setup_quality BETWEEN 1 AND 5),
  followed_rules      BOOLEAN DEFAULT TRUE,
  
  -- Notes
  notes               TEXT,
  screenshot_ref      TEXT,
  
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX ON paper_trade_journal(strategy_id, entry_date DESC);
CREATE INDEX ON paper_trade_journal(asset_class, outcome);
CREATE INDEX ON paper_trade_journal(entry_date DESC);
```

---

## RISK MANAGEMENT FRAMEWORK

### Position Sizing Rules

```python
def calculate_paper_position_size(account_balance, risk_pct, entry, stop_loss):
    """Calculate paper position size based on fixed risk percentage."""
    risk_amount = account_balance * risk_pct
    distance = abs(entry - stop_loss)
    if distance == 0:
        raise ValueError("Stop loss cannot equal entry price")
    return risk_amount / distance

# Example: $10,000 paper account, 1% risk, entry 1.2500, stop 1.2470
# risk_amount = $100
# distance = 30 pips = 0.0030
# position_size = $100 / 0.0030 = 33,333 units (0.33 lots)
```

### Hard Risk Limits

| Rule | Limit | Action on Breach |
|------|-------|------------------|
| Risk per trade | 1% of account | Reduce size or skip |
| Risk per trade (volatile) | 0.5% of account | For crypto/options |
| Max daily loss | 3% of account | Stop trading for the day |
| Max weekly drawdown | 6% of account | Review strategy, reduce size |
| Max monthly drawdown | 12% of account | Full strategy pause + audit |
| Consecutive losses | 4 in a row | Pause 5 sessions |
| Correlated positions | 2 max | Never hold 3 correlated assets |
| News window | ±30 min | No entries near major data |

### Drawdown Recovery Protocol

| Drawdown | Action |
|----------|--------|
| 5–8% | Reduce position size by 50%, review last 10 trades |
| 8–12% | Stop new trades, full audit of last 20 trades |
| 12%+ | Full strategy pause, return to simulation mode |

---

## WIN/LOSS EXPECTANCY FORMULAS

```python
# Core expectancy formula
def calculate_expectancy(win_rate, avg_win_r, avg_loss_r=1.0):
    """
    Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
    Positive expectancy = profitable strategy over time.
    Target: > 0.5R per trade.
    """
    loss_rate = 1 - win_rate
    return (win_rate * avg_win_r) - (loss_rate * avg_loss_r)

# Example: 50% win rate, 2R average win, 1R average loss
# Expectancy = (0.50 × 2) - (0.50 × 1) = 1.0 - 0.5 = 0.5R per trade ✅

# Profit factor
def profit_factor(gross_wins, gross_losses):
    if gross_losses == 0:
        return float('inf')
    return gross_wins / gross_losses
# Target: > 1.5

# Sharpe ratio (simplified for trading)
def simplified_sharpe(returns_list, risk_free=0):
    import statistics
    if len(returns_list) < 2:
        return 0
    avg = statistics.mean(returns_list) - risk_free
    std = statistics.stdev(returns_list)
    return avg / std if std else 0
# Target: > 1.0 annualized
```

---

## STRATEGY DEFINITIONS

### FOREX Strategy 1 — London Breakout

**ID:** `forex_london_breakout_v1`  
**Market:** GBP/USD, EUR/USD  
**Session:** London open — 3:00 AM to 5:00 AM EST  
**Timeframe:** 15-minute chart  

**Indicators:**
- Pre-session range: high and low from 7:00 PM to 2:00 AM EST
- ATR(14) — entry filter
- Volume (if broker provides)

**Market Conditions:**
- Valid: Normal volatility, not major news day
- Invalid: NFP day, FOMC, central bank announcements, holiday sessions

**Entry Rules:**
1. Identify pre-session range (7 PM – 2 AM EST)
2. Long: 15M candle closes ABOVE range high
3. Short: 15M candle closes BELOW range low
4. ATR must be > 7-day average ATR (no low-volatility entry)
5. Entry price: open of candle AFTER the breakout candle
6. No entries after 6:00 AM EST

**Exit Rules:**
- TP1: 1× range height (50% exit)
- TP2: 1.5× range height (remaining 50%)
- SL: Opposite side of range
- Trail: Move SL to breakeven when TP1 is hit

**Stop Loss:** Opposite side of the pre-session range  
**Risk per Trade:** 1% of paper account  
**Expected RR:** 1:1.5 to 1:2.5  
**Max trades/day:** 1 (first valid setup only)

**Invalidation:**
- News event within 1 hour of setup
- Range height < 15 pips (too narrow for reliable breakout)
- ATR below weekly average

**Metrics to Track:** Win rate, total R, max consecutive losses, average pips, range height at entry, ATR filter pass rate

**Minimum sample:** 30 trades before any strategy adjustment

---

### FOREX Strategy 2 — Trend Pullback (EMA Retest)

**ID:** `forex_trend_pullback_v1`  
**Market:** EUR/USD, USD/JPY, GBP/USD  
**Session:** London + NY overlap — 8:00 AM to 2:00 PM EST  
**Timeframe:** 1H trend context, 15M entry  

**Indicators:**
- EMA 20 + EMA 50 on 1H (trend filter)
- RSI(14) on 15M (pullback confirmation)
- ATR(14) on 15M (stop sizing)

**Market Conditions:**
- Valid: Clear trend on 1H (EMA 20 above 50 for uptrend, below for downtrend)
- Invalid: EMAs crossing, choppy price action, range-bound

**Entry Rules (Long example):**
1. 1H: EMA 20 above EMA 50, both sloping up
2. Price pulls back to touch EMA 20 zone on 15M
3. 15M RSI reaches 40–55 (pullback, not exhaustion)
4. 15M candle closes bullish from EMA 20 area
5. Enter on next candle open

**Exit Rules:**
- TP: Previous 1H swing high, or 2.5× ATR from entry
- SL: 1× ATR below entry candle low (long) / above (short)
- Breakeven: Move SL to breakeven at 1:1

**Risk per Trade:** 1% of paper account  
**Expected RR:** 1:2 to 1:3  
**Max trades/day:** 2 (prefer best setup quality)

**Invalidation:**
- EMA 20 slope flattens or reverses during trade
- Price closes below EMA 50 (long trade) — exit immediately
- 4+ consecutive losses — pause 3 sessions

---

### CRYPTO Strategy 1 — BTC/ETH Trend Continuation

**ID:** `crypto_trend_continuation_v1`  
**Market:** BTC/USD, ETH/USD (paper price tracking only)  
**Timeframe:** 4H chart  
**Data source:** CoinGecko API (free) or TradingView (paper tracking)

**Market Conditions:**
- Valid: All EMAs aligned (20 > 50 > 200), trending market
- Invalid: EMA compression (within 2%), sideways action

**Entry Rules:**
1. All three EMAs aligned in direction
2. MACD(12,26,9): line crosses above signal (long) or below (short)
3. Volume bar > 20-period volume moving average
4. Price above EMA 20 for longs, below for shorts
5. Enter on candle close that confirms all conditions

**Exit Rules:**
- TP1: 3× ATR from entry (scale 50% out)
- TP2: Previous swing high/low (scale remaining)
- SL: Below EMA 50 for longs / above for shorts
- Time stop: Close after 10 candles if no movement

**Risk per Trade:** 1% of paper account  
**Expected RR:** 1:2 minimum  
**Max simultaneous positions:** 1 per asset

**Invalidation:**
- BTC dominance spike during altcoin trade
- Macro risk event (Fed, CPI) within 4 hours
- 3 consecutive losses → wait for EMA realignment

---

### CRYPTO Strategy 2 — Volatility Breakout (Bollinger Squeeze)

**ID:** `crypto_volatility_breakout_v1`  
**Market:** BTC/USD, ETH/USD, SOL/USD (paper tracking)  
**Timeframe:** 1H chart  

**Setup (Squeeze Detection):**
1. Bollinger Bands(20, 2.0) width at 30-day minimum
2. ATR(14) below 20-period ATR average
3. Price consolidating inside bands for 4+ candles

**Entry Rules:**
1. Candle closes OUTSIDE the Bollinger Band
2. Volume on that candle > 2× 20-period average volume
3. Enter at open of NEXT candle
4. Do not chase if price has moved > 0.5× ATR from breakout candle close

**Exit Rules:**
- TP: 2× BB width from entry price
- SL: Back inside the band (opposite band close)
- Hard stop: 2× ATR from entry (whichever is closer)

**Risk per Trade:** 0.5% of paper account (higher volatility asset)  
**Expected RR:** 1:2 to 1:4  
**Max trades/week:** 3 (wait for true squeeze, not every compression)

**Invalidation:**
- False breakout rate > 60% over 20 trades → increase volume filter
- Price reverses back inside bands within 2 candles → exit at market

---

### OPTIONS Strategy 1 — SPY Trend Continuation

**ID:** `options_spy_trend_v1`  
**Market:** SPY (paper tracking — no contracts purchased)  
**Timeframe:** Daily trend, 30M entry timing  
**Data:** Yahoo Finance / TradingView (free, no broker needed)

**Hypothetical Paper Position:**
- Long call (uptrend): 30-delta call, 30–45 DTE
- Long put (downtrend): 30-delta put, 30–45 DTE
- Paper size: 1 contract per $10K paper account

**Setup:**
1. SPY above/below 50-day SMA (trend direction)
2. VIX below 20 (lower IV = cheaper premium)
3. 3-day pullback to 20-day SMA area
4. Day of entry: Price bounces from SMA area with volume

**Paper Entry:**
- Record: strike, expiry, theoretical premium (using options pricing calculator or TradingView)
- Track: Daily theoretical P&L based on delta × price move

**Exit Rules (paper):**
- TP: 50% of max profit (when position doubles in theory)
- SL: 200% of premium (lose 2× the premium paid)
- Time stop: Close at 21 DTE regardless

**Metrics to Track:** Paper IV at entry, VIX, DTE, delta decay over time, hypothetical premium movement

**Failure Conditions:**
- Paper losses > 20% of account → review VIX filter (use < 15 threshold)
- Win rate < 50% over 20 paper trades → review delta selection (try 40-delta)

---

### OPTIONS Strategy 2 — QQQ Momentum Breakout

**ID:** `options_qqq_momentum_v1`  
**Market:** QQQ (paper tracking)  
**Timeframe:** Daily + Weekly  

**Setup:**
1. QQQ breaks 52-week high or major resistance level
2. Weekly RSI(14) between 55–70 (momentum, not overbought)
3. Breakout confirmed with 1.5× average volume

**Paper Position:**
- ATM call, 45–60 DTE
- Paper premium tracking (1% paper account = 1 contract max)

**Exit Rules:**
- 100% paper gain → exit half, trail remainder with 50% trailing stop
- 50% paper loss → close entire position
- 30 DTE reached → close if not profitable

**Failure Conditions:**
- 3 consecutive false breakouts → pause 2 weeks, tighten volume filter to 2×

---

## DAILY/WEEKLY REPORTING FORMAT

### Daily Paper Trading Report

```
DATE: [YYYY-MM-DD]
SESSION: [London / NY / Both]
PAPER ACCOUNT VALUE: $[X,XXX]

TODAY'S TRADES:
[Strategy] [Market] [Direction] [Entry] [Exit] [Result] [R]

RUNNING TOTALS (Last 30 days):
Total trades: X
Win rate: XX%
Total R gained: +X.XR
Max drawdown: X.X%
Current streak: [X wins / X losses]

OBSERVATIONS:
- [1 thing that worked]
- [1 thing to review]

NEXT SESSION:
- [Setups to watch]
```

### Weekly Paper Performance Review

```
WEEK OF: [Mon–Fri dates]
STRATEGY UNDER REVIEW: [name]

TRADES THIS WEEK: X
WIN RATE: XX% (Target: >50%)
TOTAL R: +/-X.XR (Target: >0.5R/week)
PROFIT FACTOR: X.X (Target: >1.5)
MAX SINGLE LOSS: X.XR
MAX DRAWDOWN: X.X%

RULE ADHERENCE: X/X trades followed all rules

IMPROVEMENTS NEEDED:
1.
2.

NEXT WEEK FOCUS:
```

---

## TRADING DASHBOARD PLANNING

**Planned dashboard sections (for future nexuslive integration):**

1. **Strategy Status Cards** — one card per strategy, showing paper win rate + last 10 trades
2. **Equity Curve Chart** — paper account cumulative R over time
3. **Streak Tracker** — current win/loss streak indicator
4. **Next Setup Radar** — checklist of conditions for each strategy (real-time market state)
5. **Risk Status** — current daily/weekly drawdown vs. limits
6. **Trade Log Table** — searchable, filterable paper trade history

**Tech stack:** Nexuslive (React + Supabase) — add `paper_trade_journal` table to DB when ready
