# Nexus Trading Research Lab

**Created:** 2026-05-18  
**Status:** 7 subtasks queued | Approval PENDING (`674ac406`)  
**Mode:** PAPER ONLY — NO live execution, NO broker connection, NO real money

---

## SAFETY HARD RULES

```
LIVE_TRADING=false
REAL_MONEY_TRADING=false
TRADING_LIVE_EXECUTION_ENABLED=false
NO BROKER CONNECTION
NO API TRADING KEYS
NO AUTOMATIC ORDER EXECUTION
```

All strategy definitions are for research and paper simulation ONLY.
No live execution until 6+ months of verified paper performance AND explicit approval.

---

## Strategy Definitions

### FOREX Strategy 1 — London Breakout

**Market:** GBP/USD, EUR/USD  
**Session:** London open (3:00 AM – 5:00 AM EST)  
**Timeframe:** 15-minute chart  

**Indicators:**
- Price range of 7:00 PM – 2:00 AM EST (pre-session range)
- ATR(14) for volatility filter
- Volume (if available via data provider)

**Entry Rules:**
- Long: Price breaks above pre-session high + candle closes above
- Short: Price breaks below pre-session low + candle closes below
- Confirm with ATR > daily average (avoid low-volatility sessions)
- No entries after 6:00 AM EST (session fades)

**Exit Rules:**
- Take Profit: 1.5× the pre-session range height
- Stop Loss: Below/above pre-session range (opposite side)
- Trail stop by 50% of TP once 1:1 is reached

**Risk Per Trade:** 1% of paper account  
**Expected RR:** 1:1.5 to 1:2  
**Max trades/day:** 1  

**Metrics to Track:**
- Win rate, total R gained/lost, consecutive losses, drawdown, sessions missed

**Paper Journal Schema:**
```json
{
  "date": "YYYY-MM-DD",
  "session": "london_open",
  "pair": "GBP/USD",
  "direction": "long|short",
  "entry_price": 0.0,
  "stop_loss": 0.0,
  "take_profit": 0.0,
  "exit_price": 0.0,
  "result_r": 0.0,
  "result_pips": 0,
  "duration_minutes": 0,
  "pre_session_range_pips": 0,
  "atr_at_entry": 0.0,
  "notes": "",
  "outcome": "win|loss|breakeven|missed"
}
```

**Failure Conditions:**
- Win rate < 40% over 50 trades → pause and review
- Drawdown > 15% of paper account → stop, analyze
- 5 consecutive losses → pause 5 sessions

---

### FOREX Strategy 2 — Trend Pullback

**Market:** EUR/USD, USD/JPY, GBP/USD  
**Session:** New York or London (8:00 AM – 2:00 PM EST)  
**Timeframe:** 1H chart for trend, 15M for entry  

**Indicators:**
- EMA 20 + EMA 50 (trend direction)
- RSI(14) for pullback exhaustion
- ATR(14) for stop sizing

**Entry Rules:**
- Identify 1H trend: EMA20 above EMA50 = uptrend (reverse for downtrend)
- Wait for price to pull back to EMA20 area on 15M
- RSI on 15M pulls to 40–50 (uptrend) or 50–60 (downtrend)
- Enter on first 15M candle that closes back in trend direction
- EMA20 must be sloping in trend direction

**Exit Rules:**
- Take Profit: Previous swing high/low, or 2× ATR from entry
- Stop Loss: 1× ATR below/above entry candle low/high
- Move stop to breakeven at 1:1

**Risk Per Trade:** 1% of paper account  
**Expected RR:** 1:2 to 1:3  
**Max trades/day:** 2  

**Metrics to Track:** Same as London Breakout + EMA slope angle  

**Failure Conditions:**
- Win rate < 45% over 40 trades → review EMA parameters
- 4 consecutive losses → pause 3 sessions

---

### CRYPTO Strategy 1 — BTC/ETH Trend Continuation

**Market:** BTC/USD, ETH/USD (spot price tracking, no derivatives)  
**Timeframe:** 4H chart  
**Note:** Paper tracking only via price data — no exchange connection

**Indicators:**
- EMA 20, EMA 50, EMA 200 (trend stack)
- MACD(12,26,9) for momentum
- Volume MA(20) for confirmation

**Entry Rules:**
- All three EMAs aligned (20 > 50 > 200 = bullish, reverse = bearish)
- MACD line crosses above signal line (long) or below (short)
- Volume bar > Volume MA at entry candle
- Price above EMA 20 for longs, below for shorts

**Exit Rules:**
- Take Profit: 3× ATR from entry (target 1), previous swing high (target 2)
- Stop Loss: Below EMA 50 for longs, above for shorts
- Partial exit (50%) at target 1, trail remainder

**Risk Per Trade:** 1% of paper account  
**Expected RR:** 1:2 minimum  
**Max positions:** 1 per asset simultaneously  

**Failure Conditions:**
- 3 consecutive losses → check if market is ranging (EMA compression)
- Win rate < 50% over 30 trades → review entry timing

---

### CRYPTO Strategy 2 — Volatility Breakout

**Market:** BTC/USD, ETH/USD, SOL/USD  
**Timeframe:** 1H chart  

**Indicators:**
- Bollinger Bands(20, 2.0) for squeeze detection
- ATR(14) for volatility measurement
- Volume MA(20)

**Setup:**
- Bollinger Band width contracts to 30-day low (squeeze)
- ATR below 20-period average
- Wait for candle close outside BB with 2× average volume

**Entry Rules:**
- Long: Close above upper BB with high volume
- Short: Close below lower BB with high volume
- Enter on next candle open

**Exit Rules:**
- Take Profit: 2× BB width from entry
- Stop Loss: Back inside BB (opposite band)
- Hard stop: 2× ATR from entry

**Risk Per Trade:** 0.5% of paper account (higher volatility)  
**Expected RR:** 1:2 to 1:4  

**Failure Conditions:**
- False breakouts > 60% → tighten volume filter
- Drawdown > 10% → pause strategy

---

### OPTIONS Strategy 1 — SPY Trend Continuation

**Market:** SPY (tracking only — NO options contracts purchased)  
**Timeframe:** Daily chart for trend, 30M for entry timing  
**Safety note:** Paper tracking of hypothetical options P&L using historical pricing only

**Setup:**
- SPY above 50-day SMA in uptrend (reverse for downtrend)
- VIX below 20 (calm market, options cheaper)
- Wait for 3-day pullback to 20-day SMA area

**Hypothetical Position (paper):**
- Long: 30-delta call, 21-45 DTE
- Short: 30-delta put, 21-45 DTE
- Size: 1 contract per $10,000 of paper account

**Exit Rules (paper):**
- Profit target: 50% of max profit
- Stop loss: 200% of premium paid
- Time stop: Close at 21 DTE regardless

**Risk Per Trade:** 1% of paper account premium  
**Expected RR:** Track empirically  

**Metrics to Track:** Paper premium cost, P&L at expiry, IV at entry, VIX level  

**Failure Conditions:**
- Paper losses > 20% of account → stop, review VIX filter
- Win rate < 50% over 20 trades → review delta selection

---

### OPTIONS Strategy 2 — QQQ Momentum Breakout

**Market:** QQQ (tracking only — paper)  
**Timeframe:** Daily + Weekly  

**Setup:**
- QQQ breaks above 52-week high or major resistance with high volume
- RSI(14) on weekly between 55–70 (momentum, not overbought)

**Hypothetical Position (paper):**
- Long: ATM call, 45-60 DTE, on breakout confirmation
- Size: 1% paper risk on premium

**Exit Rules:**
- 100% gain → sell half, trail remainder
- 50% loss → close position
- 30 DTE reached → close if not profitable

**Failure Conditions:**
- Breakout fails (price returns below level) within 3 sessions → exit
- 3 consecutive false breakouts → pause strategy 2 weeks

---

## Paper Trading Journal Schema (Universal)

```sql
-- Paper trade journal table (run in dev or as local file)
CREATE TABLE paper_trades (
  id              TEXT PRIMARY KEY,
  strategy_name   TEXT NOT NULL,
  market          TEXT NOT NULL,
  timeframe       TEXT,
  direction       TEXT CHECK (direction IN ('long', 'short', 'neutral')),
  entry_date      DATE NOT NULL,
  entry_price     DECIMAL(18,8),
  stop_loss       DECIMAL(18,8),
  take_profit     DECIMAL(18,8),
  exit_date       DATE,
  exit_price      DECIMAL(18,8),
  result_r        DECIMAL(8,4),
  result_pct      DECIMAL(8,4),
  paper_pnl_usd   DECIMAL(12,2),
  outcome         TEXT CHECK (outcome IN ('win','loss','breakeven','open','missed')),
  setup_quality   INTEGER CHECK (setup_quality BETWEEN 1 AND 5),
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Risk Management Rules

1. **Max risk per trade:** 1% of paper account (0.5% for volatility strategies)
2. **Max daily loss:** 3% of paper account → stop trading that day
3. **Max weekly drawdown:** 6% → review strategy parameters
4. **Max monthly drawdown:** 10% → full strategy review
5. **Consecutive losses:** 4 in a row → pause 5 sessions minimum
6. **Correlation rule:** Never have 2 positions in correlated assets simultaneously
7. **News filter:** No entries within 30 minutes of major economic data
8. **Review cadence:** Weekly paper performance review with Nexus

---

## Paper Performance Tracking Metrics

| Metric | Target | Alert Level |
|--------|--------|-------------|
| Win Rate | >50% | <40% |
| Avg RR | >1.5:1 | <1.0:1 |
| Expectancy | >0.5R | <0R |
| Max Drawdown | <15% | >10% |
| Profit Factor | >1.5 | <1.0 |

---

## Approval Status

To activate Trading Research Lab subtasks:
```bash
python3 bin/nexus approvals list
python3 bin/nexus approvals approve 674ac406-b3e8-446a-aa3d-c31bd61c83a9
```

After approval: research_worker will generate structured strategy specs.
