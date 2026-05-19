# Nexus Trading Research Lab — Strategy Specifications
# Paper Trading ONLY · No Live Execution · No Real Money · Educational Research

**Status:** ACTIVE — Paper testing phase  
**Updated:** 2026-05-19  
**Safety:** NEXUS_DRY_RUN=true · LIVE_TRADING=false · REAL_MONEY_TRADING=false  
**Minimum paper period before any live consideration:** 6 months verified performance

---

## SAFETY CONSTRAINTS (NON-NEGOTIABLE)

- All entries here are **research and simulation only**
- `is_paper_trade = TRUE` enforced at database level (CHECK constraint)
- `live_trading_enabled = FALSE` enforced at database level (CHECK constraint)
- No broker API connections
- No auto-execution
- No financial guarantees — past paper performance does not guarantee future results

---

## STRATEGY 1 — FOREX: London Breakout

**ID:** `forex_london_breakout_v1`  
**Market:** GBP/USD, EUR/USD, GBP/JPY  
**Timeframe:** 15M  
**Session:** London Open (07:00–09:00 UTC)  
**Asset Class:** Forex

### Setup Logic
- Identify the consolidation range from 04:00–07:00 UTC (Asian session close)
- Range height must be < 1.5× ATR(14) on the 15M chart
- Breakout candle must close **above range high** (long) or **below range low** (short)

### Entry Rules
1. Wait for the first 15M candle **close** outside the range
2. Enter at the open of the next candle (no chasing — skip if price has moved >50% of ATR from range edge)
3. ATR filter: ATR(14) on 15M must be above the 7-day ATR average
4. No entries within 30 minutes of news events (NFP, CPI, rate decisions)
5. Max 1 active trade per session

### Exit Rules
- **Stop Loss:** Below the range low (long) / above range high (short) + 5 pips buffer
- **Take Profit 1 (50% position):** 1.5× risk distance
- **Take Profit 2 (50% position):** 3× risk distance
- **Trailing stop:** Move SL to breakeven after TP1 hit

### Invalidation Conditions
- Price wicks back inside range after breakout → close immediately
- EMA 20 slope is flat or opposite on the 1H chart → skip
- News within next 60 minutes → skip

### Risk Parameters
- **Risk per trade:** 1% of paper account
- **Max daily loss:** 3% (3 consecutive losses → stop for the day)
- **Max RR target:** 3:1
- **Expected win rate:** 45–55% (positive expectancy at 3:1 RR)

### Expected Metrics (Paper Targets)
| Metric | Target |
|--------|--------|
| Win Rate | 48–55% |
| Average R | +1.4R per trade |
| Profit Factor | 1.3–1.6 |
| Max Drawdown | < 8% |
| Monthly trades | 15–25 |

### Journaling Fields Required
- Range height (pips)
- ATR at entry
- News nearby (Y/N)
- Session (always London)
- Entry reason, exit reason
- Setup quality (1–5)
- Followed rules (Y/N)

---

## STRATEGY 2 — FOREX: Trend Pullback (EMA 20 Retest)

**ID:** `forex_trend_pullback_v1`  
**Market:** EUR/USD, GBP/USD, USD/JPY  
**Timeframe:** 15M (signal), 1H (trend filter)  
**Session:** London/NY Overlap (13:00–16:00 UTC)  
**Asset Class:** Forex

### Setup Logic
- 1H chart: price above EMA 50 + EMA 200 (uptrend) or below (downtrend)
- 15M chart: price pulls back to EMA 20
- RSI(14) must be between 40–60 at pullback (avoiding extreme momentum entries)
- Look for bullish/bearish engulfing candle at EMA 20 zone

### Entry Rules
1. 1H trend confirmed (EMA 50 slope clear)
2. 15M price touches EMA 20 zone (within 5 pips)
3. RSI 40–60 at pullback touch
4. Engulfing or pin bar candle closes at EMA 20
5. Enter at next candle open

### Exit Rules
- **Stop Loss:** Below the pullback low + 5 pips (long) / above pullback high + 5 pips (short)
- **TP1 (50%):** Previous swing high/low
- **TP2 (50%):** 2× risk distance
- **Invalidation exit:** EMA 20 slope reverses while in trade → close at market

### Invalidation Conditions
- 1H EMA 50 and 200 are tangled / flat → skip
- RSI at pullback < 35 or > 65 → momentum too strong, skip
- EMA 20 slope opposite to trade direction

### Risk Parameters
- **Risk per trade:** 1%
- **Max daily loss:** 3%
- **RR target:** 2:1 minimum

### Expected Metrics (Paper Targets)
| Metric | Target |
|--------|--------|
| Win Rate | 52–60% |
| Average R | +1.2R |
| Profit Factor | 1.4–1.8 |
| Max Drawdown | < 6% |
| Monthly trades | 20–35 |

---

## STRATEGY 3 — CRYPTO: BTC/ETH Trend Continuation

**ID:** `crypto_trend_continuation_v1`  
**Market:** BTC/USD, ETH/USD  
**Timeframe:** 4H (signal), 1D (trend filter)  
**Session:** N/A (24/7 — avoid low-volume weekends)  
**Asset Class:** Crypto

### Setup Logic
- 1D chart: all three EMAs aligned (20 > 50 > 200) = uptrend
- MACD histogram positive and crossing up on 4H
- Volume above 20-period average on the entry candle
- BTC dominance stable or rising (for BTC trades)

### Entry Rules
1. Daily trend confirmed (EMAs aligned)
2. 4H MACD line crosses above signal line
3. 4H volume > 20-period average
4. Entry on next 4H candle open after cross
5. No entries when BTC has moved > 5% in last 24H (volatility filter)

### Exit Rules
- **Stop Loss:** Below most recent 4H swing low
- **TP1 (30%):** 3× ATR from entry
- **TP2 (40%):** Previous major resistance level
- **TP3 (30%):** Trailing stop — 2× ATR trailing

### Invalidation Conditions
- Daily EMA 20 slope turns negative
- MACD divergence (price making higher highs, MACD making lower highs)
- Funding rate extremely positive (> 0.1% per 8H) → overheated longs, skip

### Risk Parameters
- **Risk per trade:** 1%
- **Position sizing:** Based on distance from entry to SL
- **Max concurrent crypto positions:** 2

### Expected Metrics (Paper Targets)
| Metric | Target |
|--------|--------|
| Win Rate | 45–55% |
| Average R | +2.0R |
| Profit Factor | 1.5–2.0 |
| Max Drawdown | < 12% |
| Monthly trades | 8–15 |

**Note:** Crypto has higher volatility — wider stops required. Paper test extensively before any consideration.

---

## STRATEGY 4 — CRYPTO: Volatility Breakout

**ID:** `crypto_volatility_breakout_v1`  
**Market:** BTC/USD, ETH/USD, SOL/USD  
**Timeframe:** 1H  
**Session:** N/A (any — best results observed during NY session overlap)  
**Asset Class:** Crypto

### Setup Logic
- Identify consolidation: Bollinger Band squeeze (BB width < 20th percentile of last 50 bars)
- Price coils for 4+ hours within 2% range
- Volume drops to < 50% of 20-period average during squeeze
- Watch for breakout candle with volume spike

### Entry Rules
1. BB squeeze confirmed (4+ bars)
2. Volume drops during consolidation
3. Breakout candle closes > 1.5% outside Bollinger Band
4. Volume on breakout candle > 2× previous 3-candle average
5. Enter on breakout candle close (aggressive) or next candle open (conservative)

### Exit Rules
- **Stop Loss:** Mid-point of the squeeze range
- **TP1 (50%):** 2× the squeeze range height from breakout point
- **TP2 (50%):** 3× the squeeze range height
- **Time stop:** If trade doesn't reach TP1 within 12 hours → close

### Invalidation Conditions
- Volume spike on breakout < 1.5× average → false breakout risk, skip
- Bitcoin moving opposite direction on 4H → skip altcoin breakouts
- News-driven spike without consolidation setup

### Risk Parameters
- **Risk per trade:** 0.75% (wider stops → smaller risk %)
- **Max daily crypto exposure:** 2% across all positions

### Expected Metrics (Paper Targets)
| Metric | Target |
|--------|--------|
| Win Rate | 40–50% |
| Average R | +2.5R |
| Profit Factor | 1.4–1.7 |
| Max Drawdown | < 15% |
| Monthly trades | 6–10 |

---

## STRATEGY 5 — OPTIONS: SPY Trend Continuation

**ID:** `options_spy_trend_v1`  
**Market:** SPY (S&P 500 ETF)  
**Timeframe:** Daily signal, 4H confirmation  
**Session:** US Market Hours (09:30–16:00 ET)  
**Asset Class:** Options (paper only — no real options contracts)

**IMPORTANT:** Options paper trading = tracking hypothetical option contracts at current prices. No real broker connections. No real contracts.

### Setup Logic
- SPY daily chart: price above 50-day SMA and 200-day SMA (bull trend)
- 4H RSI > 50, EMA 20 slope positive
- VIX below 20 (low volatility environment — premium sellers have edge)
- Identify pullback to daily 20-EMA support zone

### Paper Trade Structure
- **Type:** Long call (bullish) or long put (bearish)
- **Strike:** ATM or 1 strike OTM
- **Expiry:** 21–35 DTE (to avoid theta decay acceleration)
- **Max risk (paper):** 2% of paper account per trade (option premium)

### Entry Rules
1. SPY above 50-day + 200-day SMA
2. 4H EMA 20 acting as support (price touches and bounces)
3. RSI 45–55 zone (not overbought on 4H)
4. VIX < 20
5. Enter on confirmation candle (bullish close from EMA zone)

### Exit Rules
- **Max loss:** 50% of premium paid → close trade
- **Profit target:** 100% gain on premium (2:1 on premium)
- **Time exit:** Exit at 50% of DTE remaining (avoid gamma risk)

### Invalidation Conditions
- VIX spikes > 25 → exit all long options immediately
- SPY closes below 200-day SMA → invalidation
- Earnings within 5 days → skip (vol crush risk)

### Risk Parameters (Paper)
- **Max paper option positions:** 3 concurrent
- **Max paper portfolio at risk:** 6% (2% × 3)

### Expected Paper Metrics
| Metric | Target |
|--------|--------|
| Win Rate | 45–55% |
| Average R | +1.5R on premium |
| Max Loss per trade | 50% of premium |
| Monthly paper trades | 5–10 |

---

## STRATEGY 6 — OPTIONS: QQQ Momentum Breakout

**ID:** `options_qqq_momentum_v1`  
**Market:** QQQ (Nasdaq-100 ETF)  
**Timeframe:** Daily  
**Session:** US Market Hours  
**Asset Class:** Options (paper only)

### Setup Logic
- QQQ breaks above a well-defined resistance level with strong volume
- Daily RSI crosses above 60 on the breakout day
- Breakout candle volume > 1.5× 20-day average
- MACD histogram positive and expanding

### Paper Trade Structure
- **Type:** Long call
- **Strike:** ATM at time of breakout
- **Expiry:** 30–45 DTE
- **Entry timing:** Buy call on breakout day close or next morning open

### Entry Rules
1. Daily resistance clearly defined (tested 2+ times)
2. Daily close above resistance with volume confirmation
3. RSI crosses above 60 on breakout day
4. MACD positive and expanding
5. VIX < 22 at entry

### Exit Rules
- **Profit target:** 100–150% gain on premium
- **Stop loss:** 40% loss on premium
- **Time exit:** With 50% DTE remaining if not at profit target

### Expected Paper Metrics
| Metric | Target |
|--------|--------|
| Win Rate | 40–50% |
| Average R | +2.0R on premium |
| Monthly paper trades | 4–8 |

---

## JOURNALING SCHEMA

All paper trades logged to `paper_trade_journal` table in Supabase with:

```sql
-- Safety constraint (DB level, cannot be bypassed):
CHECK (is_paper_trade = TRUE AND live_trading_enabled = FALSE)
```

### Required Fields Per Entry
| Field | Description |
|-------|-------------|
| strategy_id | e.g. `forex_london_breakout_v1` |
| market | e.g. `GBP/USD` |
| entry_date / entry_price | When and where entered |
| stop_loss | Calculated at entry |
| take_profit_1/2 | Calculated at entry |
| risk_pct | 1% default |
| position_size | Units/lots (paper) |
| outcome | win/loss/breakeven/open/missed/skipped |
| result_r | R-multiple outcome |
| setup_quality | 1–5 rating |
| followed_rules | Boolean — key for system learning |
| notes | Observations for review |

---

## EXPECTANCY FORMULA

```
Expectancy = (Win Rate × Avg Win R) - (Loss Rate × Avg Loss R)
```

Target: Expectancy > 0.3R per trade for any strategy to be considered for extended paper testing.

Example — London Breakout:
- Win Rate 50%, Avg Win 2.5R, Loss Rate 50%, Avg Loss 1R
- Expectancy = (0.50 × 2.5) - (0.50 × 1.0) = 1.25 - 0.50 = **+0.75R**

---

## SESSION PERFORMANCE PRIORITY

| Session | Quality | Strategies Active |
|---------|---------|-------------------|
| London (07:00–11:00 UTC) | ★★★★★ | London Breakout, EMA Pullback |
| London/NY Overlap (13:00–16:00 UTC) | ★★★★★ | EMA Pullback, SPY/QQQ Options |
| NY (16:00–20:00 UTC) | ★★★☆☆ | Options only |
| Asia (00:00–07:00 UTC) | ★★☆☆☆ | Avoid (historically lowest WR) |
| Crypto | ★★★★☆ | Any session, avoid low-volume weekends |

---

## PROGRESSION GATES

Before any strategy moves beyond paper testing:

1. **Gate 1 (Month 1–3):** Minimum 30 paper trades with documented journal entries
2. **Gate 2 (Month 3–6):** Consistent positive expectancy (> 0.3R) over 50+ trades
3. **Gate 3 (Month 6):** Full 6-month paper review — win rate, profit factor, max drawdown all meet targets
4. **Gate 4 (If considering live):** Operator review + explicit approval + separate risk discussion

No automated progression. Each gate requires manual review by Ray.

---

*Educational research only. Not financial advice. No guarantees. Paper trading results do not guarantee live trading results.*
