# Forex Operations System
**Owner:** Raymond Davis  
**Mode:** Paper trading only  
**Instruments:** EUR/USD · GBP/USD · XAU/USD  
**Date:** 2026-05-11

---

## Session Dashboard

```
╔══════════════════════════════════════════════════════════════════════╗
║                    FOREX OPERATIONS CENTER                           ║
╠═════════════════════════╦════════════════════════════════════════════╣
║  ACTIVE SESSION         ║  TODAY'S WATCHLIST                        ║
║  ─────────────────────  ║  ─────────────────────────────────────── ║
║  London Open  08:00 GMT ║  EUR/USD  ▶ Watching 1.0850 break        ║
║  NY Open      13:00 GMT ║  GBP/USD  ▶ In range, wait for trigger   ║
║  Overlap      13-17 GMT ║  XAU/USD  ▶ DXY inverse watch           ║
║  ████████████░░░░░░░░░  ║                                           ║
║  [====NOW====]          ║  BEST SESSION: London/NY Overlap          ║
╠═════════════════════════╩════════════════════════════════════════════╣
║  RISK CALCULATOR                                                     ║
║  Account Size: $10,000 (simulated)                                  ║
║  Risk per trade: 1% → $100 max risk                                 ║
║  Stop: 20 pips → Position: 0.5 lots (EUR/USD)                      ║
║  Stop: 30 pips → Position: 0.33 lots (XAU/USD adj.)                ║
╠══════════════════════════════════════════════════════════════════════╣
║  TODAY'S METRICS         WIN  │ LOSS │ NET PIPS │ DISCIPLINE SCORE  ║
║  ─────────────────────  ─────┼──────┼──────────┼────────────────── ║
║  Trades taken: 0          0  │  0   │    0     │  ⭐⭐⭐⭐⭐ 100%    ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Session Timeline

```
 4am    6am    8am   10am   12pm    2pm    4pm    6pm    8pm
  │      │      │      │      │      │      │      │      │
  ░░░░░░░░      │      │      │      │      │      │      │  Tokyo open
         ████████████████      │      │      │      │      │  London session
                ░░░░░░░░░░░░░░░│      │      │      │      │  London momentum
                        ████████████████████│      │      │  NY open
                               ▓▓▓▓▓▓▓▓▓▓▓▓▓      │      │  OVERLAP ← FOCUS
                                             ░░░░░░│      │  NY wind-down
                                                   │██████│  NY close

  PRIORITY ZONES:
  ████ = High probability session window
  ▓▓▓▓ = Best volume + directional clarity (London/NY overlap 08:00-12:00 EST)
  ░░░░ = Monitor only, reduced size
```

---

## Setup Playbook

### Setup A — London Breakout Continuation
```
CRITERIA:
  ✓ Price consolidates in London first 2 hours
  ✓ Break of range with momentum candle
  ✓ Volume/ATR expansion confirms
  ✓ No major news within 30 min of entry

ENTRY:   Pullback to breakout level (limit order)
STOP:    Below range low (long) / above range high (short)
TARGET:  1.5–2.0× risk
SIZE:    1% account risk max

SETUP CARD:
┌─────────────────────────────────────┐
│  EUR/USD LONG SETUP                 │
│  ─────────────────────────────────  │
│  Range: 1.0830 - 1.0855            │
│  Break: above 1.0855               │
│  Entry: 1.0850 pullback            │
│  Stop:  1.0828 (-22 pips)          │
│  T1:    1.0883 (+33 pips) 1.5R     │
│  T2:    1.0894 (+44 pips) 2.0R     │
│  Risk:  $100 (1% sim account)      │
└─────────────────────────────────────┘
```

### Setup B — NY Open Momentum
```
CRITERIA:
  ✓ Trend established in London session
  ✓ NY open confirms same direction
  ✓ 1h or 4h higher-high/higher-low structure intact
  ✓ Entry on first pullback to session VWAP or structure level

ENTRY:   Market or limit on pullback
STOP:    Below swing low / above swing high
TARGET:  2.0R minimum (NY has follow-through capacity)
```

### Setup C — XAU/USD DXY Inverse
```
CRITERIA:
  ✓ DXY showing clear directional bias
  ✓ Gold inverse correlation active (not diverging)
  ✓ Gold at key S/R level (round numbers, prior highs/lows)
  ✓ Risk events checked (CPI, FOMC days → NO TRADE)

NOTE:    XAU has wider spreads — use 30-pip stops minimum
         Size accordingly: 0.1 lots per $100 risk at 30-pip stop
```

---

## Trade Journal Template

```
DATE: ___________  SESSION: London / NY / Overlap

INSTRUMENT:  ___________
DIRECTION:   Long / Short
SETUP TYPE:  A / B / C
TIMEFRAME:   1H / 4H / 15M trigger

PRE-TRADE CHECKLIST:
  □ Trend direction confirmed on higher TF
  □ Setup criteria fully met (not "close enough")
  □ Risk/reward ≥ 1.5R
  □ No major news in next 60 min
  □ Position size calculated
  □ Emotional state: Calm / Neutral / [SKIP]

ENTRY:  ________ at ________
STOP:   ________ (_____ pips)
T1:     ________ (_____ pips / _____R)
T2:     ________ (_____ pips / _____R)
SIZE:   _____ lots = $_____ risk

RESULT:
  Exit: ________  P/L: +/- _____ pips  +/- $_____
  Outcome: Win / Loss / Breakeven

POST-TRADE REVIEW:
  Did I follow the plan? Yes / No
  What I did well: _________________________
  What to improve: _________________________
  Emotional note: _________________________
```

---

## Win/Loss Metrics Dashboard

```
╔══════════════════════════════════════════════════════╗
║           FOREX PERFORMANCE TRACKER                   ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  WEEK:  ___________    MONTH:  ___________           ║
║                                                      ║
║  Trades:    0          Win Rate:   ---%              ║
║  Wins:      0          Avg Win:    +--- pips         ║
║  Losses:    0          Avg Loss:   ----- pips        ║
║  BE:        0          Expectancy: ---               ║
║                                                      ║
║  Net Pips:  ---        Sim P/L:   $---               ║
║                                                      ║
║  ─────────────────────────────────────────────────  ║
║  DISCIPLINE SCORE                                    ║
║  Plan-following rate: ---% (target: ≥90%)            ║
║  Skipped bad setups:  ---  (quality over quantity)   ║
║  Emotional overrides: 0    (target: 0)               ║
║                                                      ║
║  ─────────────────────────────────────────────────  ║
║  EDGE QUALITY MONITOR                               ║
║  Setup A win rate: ---%  (target: ≥55%)              ║
║  Setup B win rate: ---%  (target: ≥55%)              ║
║  Setup C win rate: ---%  (target: ≥50%)              ║
╚══════════════════════════════════════════════════════╝
```

---

## Daily Forex Routine

| Time (EST) | Action |
|---|---|
| 7:30am | Check overnight range — EUR/USD, GBP/USD levels |
| 8:00am | London session review — any setups forming? |
| 9:00-9:30am | NY open — confirm or invalidate London direction |
| 9:30-12pm | **Primary execution window** (overlap) |
| 12pm | Review open positions, protect profits if applicable |
| 4pm | Day close recap — journal, metrics update |

---

## Risk Management Rules (Forex-Specific)

| Rule | Limit |
|---|---|
| Max risk per trade | 1% of sim account ($100) |
| Max trades per day | 3 |
| Daily loss limit | 2% ($200) → STOP for the day |
| Weekly loss limit | 4% ($400) → Review + reduce size |
| Minimum R:R ratio | 1.5R (no exceptions) |
| Setup quality | All criteria must be met — no "almost" entries |
| News filter | No trades 30 min before/after scheduled news |

**Hard rule:** If daily loss limit hit → close platform, do not check charts again until next day.
