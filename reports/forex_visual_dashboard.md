# Forex Visual Dashboard
**Owner:** Raymond Davis  
**Mode:** Paper trading only  
**Design:** Session-aware · Setup cards · Execution-first  
**Date:** 2026-05-11

---

## Forex Command Center — Desktop

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│   FOREX OPERATIONS CENTER            EUR/USD · GBP/USD · XAU/USD               │
│   Tuesday, May 12  ·  09:34 EST  ·  London/NY OVERLAP  ·  ⏱ 2h26m remaining  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────┐  ┌───────────────────────────────────────────┐
│   SESSION CLOCK                   │  │   MARKET CONDITIONS                       │
│   ─────────────────────────────   │  │   ─────────────────────────────────────   │
│                                   │  │                                           │
│   LONDON   ████████████████░░░░   │  │   EUR/USD  1.0847  ▲ +0.0012 (+0.11%)   │
│   4am ──────────────────── 12pm   │  │   GBP/USD  1.2634  ▼ -0.0008 (-0.06%)   │
│                                   │  │   XAU/USD  2,384   ▲ +4.20  (+0.18%)    │
│   NY       ░░░░░░████████████░░   │  │   DXY      104.2   ▼ -0.21  (-0.20%)    │
│   9am ──────────────────── 5pm    │  │                                           │
│                                   │  │   ATR(14) EUR: 68 pips   ← NORMAL        │
│   ▓▓▓▓ OVERLAP NOW ▓▓▓▓▓▓▓▓▓▓▓  │  │   ATR(14) GBP: 82 pips                   │
│   Best window: until 12:00 EST   │  │   ATR(14) XAU: $18.40                    │
└───────────────────────────────────┘  └───────────────────────────────────────────┘
```

---

## Setup Confidence Cards

```
ACTIVE WATCHLIST
══════════════════════════════════════════════════════════════════════════════════

  ┌────────────────────────────────────────┐
  │  EUR/USD  ·  SETUP A SCAN              │
  │  London Breakout Continuation          │
  │  ─────────────────────────────────     │
  │                                        │
  │  Range detected:  1.0831 – 1.0859     │
  │  Break level:     1.0860              │
  │  Current price:   1.0847              │
  │  Distance to break:  13 pips          │
  │                                        │
  │  CRITERIA CHECK:                       │
  │  ■ London consolidation 2hrs    ✅     │
  │  □ Break of range + momentum    ⏳     │
  │  □ ATR expansion confirmed      ⏳     │
  │  ■ No news within 30 min        ✅     │
  │  ■ R/R ≥ 1.5 if setup forms     ✅     │
  │                                        │
  │  CONFIDENCE:  ──────────────── 60%    │
  │               ████████████░░░░░░░░    │
  │                                        │
  │  STATUS:  🟡 WATCHING — Not triggered │
  │  ACTION:  Set alert at 1.0860         │
  │                                        │
  │  IF TRIGGERED:                         │
  │  Entry:  1.0853 (pullback)            │
  │  Stop:   1.0829  (-24 pips)           │
  │  T1:     1.0889  (+36 pips)  1.5R    │
  │  T2:     1.0901  (+48 pips)  2.0R    │
  │  Risk:   $100 · 0.42 lots            │
  └────────────────────────────────────────┘

  ┌────────────────────────────────────────┐  ┌────────────────────────────────────────┐
  │  GBP/USD  ·  MONITORING               │  │  XAU/USD  ·  SETUP C SCAN             │
  │  ─────────────────────────────────    │  │  DXY Inverse Correlation              │
  │                                       │  │  ─────────────────────────────────    │
  │  Current:   1.2634                   │  │                                        │
  │  Session range:  1.2611 – 1.2649    │  │  XAU/USD:  2,384  ▲                   │
  │                                       │  │  DXY:      104.2  ▼ (inverse active)  │
  │  Setup B criteria (NY Momentum):     │  │                                        │
  │  □ London trend confirmed     ⚠️     │  │  DXY correlation:  ACTIVE ✅          │
  │  □ NY confirm same direction  ⏳     │  │  At key S/R level: 2,400 resistance   │
  │  □ Pullback to session VWAP   ⏳     │  │                                        │
  │                                       │  │  Criteria check:                       │
  │  CONFIDENCE:  ░░░░░░░░░░░░░░░  25%  │  │  ■ DXY directional bias    ✅         │
  │  STATUS:  🔴 NO SETUP — Monitor     │  │  ■ Inverse correlation on  ✅         │
  │                                       │  │  □ At key S/R level       ⚠️ Near   │
  └────────────────────────────────────────┘  │  ■ No major events today  ✅         │
                                              │                                        │
                                              │  CONFIDENCE:  ████████░░░░░░░  55%   │
                                              │  STATUS:  🟡 DEVELOPING             │
                                              └────────────────────────────────────────┘
```

---

## Active Trade Card (Template — Paper Trade)

```
ACTIVE TRADE CARD (Paper Mode)
══════════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────────────┐
  │   ◈ EUR/USD LONG  ·  Setup A  ·  Paper Trade #001                       │
  │   ─────────────────────────────────────────────────────────────────────  │
  │                                                                          │
  │   ENTRY:    1.0853   ·   09:47 EST   ·   0.42 lots                     │
  │   STOP:     1.0829   ·   (-24 pips)  ·   Max loss: $100                │
  │   T1:       1.0889   ·   (+36 pips)  ·   1.5R  =  $150                 │
  │   T2:       1.0901   ·   (+48 pips)  ·   2.0R  =  $200                 │
  │                                                                          │
  │   CURRENT:  1.0868   ·   (+15 pips)  ·   +$63.00                       │
  │                                                                          │
  │   PROGRESS TO T1:                                                        │
  │   Entry ━━━━━━━━━━━━━━━━◆━━━━━━━━━━━━━━━━━━━━━━━ T1                   │
  │   1.0853   1.0860   1.0868   1.0875   1.0882   1.0889                  │
  │                  ↑ HERE                                                  │
  │   ████████████████████████░░░░░░░░░░░░░░░░░░░░░░   42% to T1           │
  │                                                                          │
  │   Time in trade:  00:47    Setup quality: 4/5 ⭐⭐⭐⭐                    │
  │   Emotional state logged:  Calm ✅                                      │
  │   Plan deviation:  None ✅                                               │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## Risk Gauge Panel

```
RISK CONTROL CENTER
══════════════════════════════════════════════════════════════════════════════════

  ┌───────────────────────────────────────────────────────────────────────┐
  │   DAILY RISK GAUGE                                                     │
  │                                                                        │
  │   SAFE        ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  DAILY LIMIT      │
  │   |           |              |              |        |                  │
  │   $0         $50           $100           $150      $200 ← STOP       │
  │                                                                        │
  │   Current exposure:  $0.00   (0% of daily limit)                      │
  │   Remaining budget:  $200.00 (full day available)                      │
  │                                                                        │
  │   TRADE COUNT:  0/3   ●○○  (max 3 trades/day)                        │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────┐    ┌─────────────────────┐    ┌────────────────────┐
  │   WIN STREAK        │    │   LOSS STREAK        │    │  WEEKLY P/L        │
  │                     │    │                      │    │                    │
  │   ○ ○ ○ ○ ○         │    │   ○ ○ ○ ○ ○          │    │  Mon  +$0.00       │
  │   0 wins in a row   │    │   0 losses in row    │    │  Tue  +$0.00       │
  │                     │    │                      │    │  Wed  ---          │
  │   Best: 0           │    │   Max allowed: 2     │    │  Thu  ---          │
  │   Target: 3+ wins   │    │   (then review)      │    │  Fri  ---          │
  │   then note edge    │    │   ✅ None today       │    │  ──────────────    │
  └─────────────────────┘    └─────────────────────┘    │  Total  +$0.00     │
                                                          └────────────────────┘
```

---

## Session Heatmap — Market Hours

```
FOREX SESSION HEATMAP (Volatility + Probability)
══════════════════════════════════════════════════════════════════════════════════

  HOUR       │ 4am  5am  6am  7am  8am  9am  10am 11am 12pm 1pm  2pm  3pm  4pm
  ───────────┼──────────────────────────────────────────────────────────────────
  PROBABILITY│  ░    ░    ▒    ▒    █    █    █    █    ▓    ▓    ▒    ░    ░
  VOLUME     │  Low  Low  Med  Med  High High High High Peak Peak Med  Low  Low
  SPREAD     │  Wide Wide Norm Norm Tight Tgt  Tgt  Tgt  Tgt  Tgt  Norm Wide Wide
  DIRECTION  │  ──   ──   ↑↑   ↑↑   ↑↑↑  ↑↑↑  ↑↑↑  ↑↑   ↑↑   ↑    ↓↓   ──   ──
  ───────────┼──────────────────────────────────────────────────────────────────
  EUR/USD    │  ░░   ░░   ▒▒   ██   ██   ██   ▓▓▓  ▓▓▓  ▒▒   ░░   ░░   ░░   ░░
  GBP/USD    │  ░░   ░░   ██   ██   ██   ██   ▓▓▓  ▓▓▓  ▒▒   ░░   ░░   ░░   ░░
  XAU/USD    │  ░░   ░░   ▒▒   ▒▒   ██   ██   ▓▓▓  ▓▓▓  ██   ▒▒   ░░   ░░   ░░

  ░ = Low   ▒ = Medium   █ = High   ▓ = Peak
  YOU ARE HERE: ↑ 10am — Prime execution window ▓▓▓
```

---

## Trade Replay Card (Post-Trade Review)

```
TRADE REPLAY — PAPER TRADE #001 (Template)
══════════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────────────┐
  │   TRADE REPLAY — EUR/USD Long · May 12, 2026                            │
  │   ─────────────────────────────────────────────────────────────────────  │
  │                                                                          │
  │                  PRICE CHART CONCEPT (text representation)              │
  │                                                                          │
  │   1.0905 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ T2 target               │
  │   1.0889 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ T1 target               │
  │   1.0870 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ /¯¯¯¯¯¯¯¯─ ─ ─                        │
  │   1.0860 ─ ─ ─ ─ ─ ─ ─ ─ ─ /  ← BREAK   ─ ─ ─ ─ ─ ─                │
  │   1.0853 ─ ─ ─ ─ ─ ─ ─ ─ /  ← ENTRY  ─ ─ ─ ─ ─ ─ ─                 │
  │   1.0845 ─ ─ ─ ─ ─ ─ ─ ─  (consolidation zone)  ─ ─ ─                │
  │   1.0831 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ Range low              │
  │   1.0829 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ STOP                   │
  │                                                                          │
  │   RESULT:   +36 pips · $150 · 1.5R · T1 hit ✅                        │
  │                                                                          │
  │   REVIEW:                                                               │
  │   Plan followed: Yes ✅                                                 │
  │   Setup quality: 4/5 — All criteria met                                │
  │   Emotion: Calm throughout — discipline maintained ✅                   │
  │   Lesson: Setup A continues to work in overlap session                 │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## Mobile Forex Card (Telegram)

```
┌──────────────────────────────────────┐
│  FOREX — Tue May 12  09:34 EST       │
│  ────────────────────────────────    │
│  EUR/USD  1.0847  ▲ +12 pips         │
│  GBP/USD  1.2634  ▼ -8 pips          │
│  XAU/USD  2,384   ▲ +4.20            │
│  DXY      104.2   ▼ (XAU bullish)    │
│  ────────────────────────────────    │
│  OVERLAP:  ▓▓▓▓▓▓▓▓▓▓░░░░  72%      │
│            2h26m remaining           │
│  ────────────────────────────────    │
│  EUR/USD: Setup A forming 🟡         │
│  Break level: 1.0860                 │
│  GBP: No setup ❌                    │
│  XAU: Watching 🟡                   │
│  ────────────────────────────────    │
│  RISK TODAY:  $0 / $200 (0%)        │
│  Trades: 0/3    Discipline: 100%    │
└──────────────────────────────────────┘
```

---

## Win/Loss Streak Visual

```
STREAK TRACKER — FOREX
══════════════════════════════════════════════════════════════════════════════════

  RECENT TRADES (newest first):
  ┌──────┬──────────┬──────────┬─────────┬────────┬────────┬──────────────────┐
  │  #   │ Pair     │ Setup    │ Result  │  Pips  │  $     │  Quality         │
  ├──────┼──────────┼──────────┼─────────┼────────┼────────┼──────────────────┤
  │  —   │  —       │   —      │   —     │   —    │   —    │  —               │
  └──────┴──────────┴──────────┴─────────┴────────┴────────┴──────────────────┘
  [No trades yet — first trade activates this tracker]

  WIN STREAK:   ○ ○ ○ ○ ○ ○ ○ ○ ○ ○   (0)
  LOSS STREAK:  ○ ○ ○ ○ ○ ○ ○ ○ ○ ○   (0)
  ON-PLAN STREAK: ● ● ● ○ ○ ○ ○ ○ ○   (3 days discipline)

  MILESTONES:
  □ First trade taken                 (0/1)
  □ First winning trade               (0/1)
  □ 3-trade win streak                (0/3)
  □ 10 trades completed               (0/10)
  □ 30 trades completed               (0/30) ← FOREX UNLOCK MILESTONE
```
