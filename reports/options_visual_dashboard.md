# Options Visual Dashboard
**Owner:** Raymond Davis  
**Mode:** Paper trading only — weekly premium cycles  
**Design:** Premium income terminal · Defined-risk only  
**Date:** 2026-05-11

---

## Options Income Command Center

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│   OPTIONS INCOME CENTER                   SPY · QQQ · Defined-Risk Only        │
│   Tuesday, May 12, 2026  ·  09:34 EST  ·  VIX: 15.2 IDEAL  ·  IVR: 42%       │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  VIX REGIME          │  │  WEEKLY PREMIUM       │  │  CYCLE PROGRESS      │  │  TOTAL PREMIUM       │
│                      │  │                       │  │                      │  │                      │
│   VIX  15.2          │  │   This week:  $0.00   │  │   Cycle 1  of 12     │  │   All-time:  $0.00   │
│   ▼ Falling          │  │   Target:     $50–150  │  │   ░░░░░░░░░░░░░░░░  │  │   Avg/wk:    $0.00   │
│                      │  │                       │  │   0/12  (0%)         │  │   Best wk:   $0.00   │
│  ████████░░░░░░░░░   │  │   Last week:  ---      │  │                      │  │   Win rate:  ---%    │
│  Low     Ideal  High  │  │   Best:       ---      │  │   ■ No undefined    │  │              0 trades│
│  ──────              │  │                       │  │     risk: ✅ 0/0    │  │                      │
│  ✅ IDEAL ZONE        │  │   ░░░░░░░░░░░░░░░░░░  │  │                      │  │   Cycles done: 0/12  │
│  Premium rich         │  │   Week starts now!   │  │   To unlock: 12 more │  │   Unlock at: 12      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

---

## Expiration Calendar

```
EXPIRATION CALENDAR — MAY 2026
══════════════════════════════════════════════════════════════════════════════════

  MON         TUE         WED         THU         FRI
  ──────────  ──────────  ──────────  ──────────  ──────────
  May 11      May 12      May 13      May 14      May 15  ◀ EXPIRY
              ← TODAY                             ← Exp day
              ENTRY DAY                           Close/expire

  May 18      May 19      May 20      May 21      May 22  ◀ EXPIRY
  Next cycle  ← ENTRY

  ┌─────────────────────────────────────────────────────────────────────────┐
  │   OPEN POSITIONS EXPIRATION MAP                                          │
  │                                                                          │
  │   May 16:   ░░░░░░░░░░░░░░░░░░░░░  [empty — no positions]              │
  │   May 23:   ░░░░░░░░░░░░░░░░░░░░░  [empty — no positions]              │
  │   Jun 20:   ░░░░░░░░░░░░░░░░░░░░░  [empty — no positions]              │
  │                                                                          │
  │   RULE: Never let positions expire unmanaged. Manage by Thu close.      │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## Strategy Cards

```
SETUP MENU — CURRENT CONDITIONS
══════════════════════════════════════════════════════════════════════════════════

  ┌────────────────────────────────────────────────────────────────┐
  │   SETUP A — BULL PUT SPREAD  ·  ✅ AVAILABLE TODAY            │
  │   ─────────────────────────────────────────────────────────   │
  │                                                                │
  │   Market:   SPY bullish / neutral  ✅                         │
  │   VIX:      15.2 — Ideal ✅                                   │
  │   IVR:      42% — Good ✅                                     │
  │   SPY:      ~$520                                             │
  │                                                                │
  │   PROPOSED TRADE (paper):                                      │
  │   Sell SPY 510P  May 16 exp                                   │
  │   Buy  SPY 505P  May 16 exp                                   │
  │   Net credit:  ~$1.20–1.50  (target)                         │
  │   Max profit:  $150  (if both expire worthless)               │
  │   Max risk:    $350  (spread - credit)                        │
  │   R: 2.3:1 (risk-to-reward on premium trades — acceptable)   │
  │                                                                │
  │   Entry window:  AFTER 10:00am (avoid open volatility)       │
  │   Close at:      50% profit = $75                            │
  │   Stop if:       loss reaches $300 (2× credit)               │
  │                                                                │
  │   CONFIDENCE:   ████████████████░░░░░░░░  70%               │
  │   STATUS:  🟢 ENTER AFTER 10AM TODAY                         │
  └────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────┐
  │   SETUP B — CASH-SECURED PUT  ·  🟡 CONSIDER                 │
  │   ─────────────────────────────────────────────────────────   │
  │   Best if you want owning SPY at lower price                  │
  │   Strike at support:  505–508                                  │
  │   Premium:  ~$2.00–2.50 (21 DTE would be richer)             │
  │   Decision: Bull Put Spread preferred this week (14 DTE)      │
  └────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────┐
  │   SETUP C — IRON CONDOR  ·  ❌ NOT THIS WEEK                 │
  │   ─────────────────────────────────────────────────────────   │
  │   VIX trending lower — range-bound play needs VIX 17+        │
  │   SPY showing directional bias — favor directional spread     │
  │   Skip IC this week                                            │
  └────────────────────────────────────────────────────────────────┘
```

---

## Spread Diagram

```
BULL PUT SPREAD VISUALIZATION
══════════════════════════════════════════════════════════════════════════════════

  SPY PRICE
  ──────────────────────────────────────────────────────────────────────────────
       480     490     500    505  510    515     520     525     530
        │       │       │      │    │      │       │       │       │
  P/L  │       │       │      │    │      │       │       │       │
  +150 │       │       │      │ ───┼──────┼───────┼───────┼───────┤  ← MAX PROFIT
        │       │       │      │    │      (above 510, both expire worthless)
    0  │       │       │      │  ╱─┤      │       │       │       │
        │       │       │    ╱─┤   │      │       │       │       │
  -350 ├───────┼───────┼──╱───┤   │      │       │       │       │  ← MAX LOSS
        │       │       │ 505  │510│      │       │       │       │
                        │      │   │
                        │      │   └── SHORT PUT (510) — sold for credit
                        │      │
                        └──────── LONG PUT (505) — bought for protection

  PROFIT ZONE:  SPY stays ABOVE 510 at expiry  ← This is our goal
  BREAKEVEN:    508.50 (approximately — 510 − net credit of ~$1.50)
  LOSS ZONE:    SPY drops below 505 at expiry
```

---

## Probability Visualization

```
PROBABILITY ANALYSIS
══════════════════════════════════════════════════════════════════════════════════

  SPY @ $520  ·  Bull Put Spread 510/505  ·  14 DTE

  PROBABILITY DISTRIBUTION (1 standard deviation = ~$14 move):

            68% of outcomes               95% of outcomes
           ←─────────────────────────────────────────────→
  ─────────┼──────────────────────────────────────────────┼────────────
   $490    $506    $510    $514    $520    $526    $534    $548    $562
     │      │       │       │       │       │       │       │       │
     │      │  ███  │  ███  │  ███  │  ███  │  ███  │  ███  │  ███  │
     │  ██  │  ███  │  ███  │  ███████████████████████████  │  ████  │
  ████████  │  ████████████████████████████████████████████████████  │ ████

             LOSS     │           PROFIT ZONE (SPY above 510)
              ZONE    ↑

  P(profit):  ~72%  (SPY stays above strike at this VIX + 14 DTE)
  Delta of short put:  ~0.22  (22% probability of being in-the-money)
  Message:  We need SPY to NOT drop 10+ points — reasonable at current VIX
```

---

## Income Tracking Dashboard

```
PREMIUM INCOME TRACKER
══════════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────────────┐
  │   WEEKLY INCOME SIMULATION                                               │
  │   ─────────────────────────────────────────────────────────────────────  │
  │                                                                          │
  │   Week 1:   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  $0  ← This week        │
  │   Week 2:   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ---                      │
  │   Week 3:   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ---                      │
  │   Week 4:   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ---                      │
  │                                                                          │
  │   TARGET LINE: ─────────────────────────────── $100/wk                  │
  │                                                                          │
  │   CUMULATIVE (12-cycle target):                                          │
  │   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  $0 / $1,200 goal        │
  │   ████████████████████████████████████████████ = unlock live options    │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## Mobile Options Card (Telegram)

```
┌─────────────────────────────────────────┐
│  OPTIONS — Tue May 12  09:34 EST        │
│  ────────────────────────────────────   │
│  VIX:   15.2   ✅ IDEAL                 │
│  IVR:   42%    ✅ Good premium          │
│  SPY:   ~$520  ▲ Bullish bias          │
│  ────────────────────────────────────   │
│  SETUP READY:                           │
│  Bull Put Spread 510/505               │
│  Credit target: ~$1.50/contract        │
│  Max risk: $350 · Max profit: $150     │
│  ────────────────────────────────────   │
│  ACTION: Enter AFTER 10:00am EST       │
│  ⚠️ Avoid first 30 min of open         │
│  ────────────────────────────────────   │
│  This week premium: $0 / $100 target   │
│  Cycle: 1/12 ░░░░░░░░░░░░░░░░░░░░░░  │
└─────────────────────────────────────────┘
```

---

## Discipline Score — Options-Specific

```
OPTIONS DISCIPLINE TRACKER
══════════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────────────┐
  │   RULES SCORECARD                          (running total)               │
  │   ─────────────────────────────────────────────────────────────────────  │
  │                                                                          │
  │   No undefined-risk positions:      ✅  0/0 violations (perfect)        │
  │   No earnings-week entries:         ✅  0/0 violations (perfect)        │
  │   Closed at 50% profit target:      ---  0 positions closed yet         │
  │   Max 2 concurrent positions:       ✅  0/2 used                        │
  │   Waited for setup criteria:        ---  First entry pending            │
  │   No FOMC/CPI violations:           ✅  0 violations                    │
  │                                                                          │
  │   OVERALL OPTIONS DISCIPLINE:   ──────────────────────── 100%           │
  │   No positions taken yet = perfect discipline so far                    │
  └──────────────────────────────────────────────────────────────────────────┘
```
