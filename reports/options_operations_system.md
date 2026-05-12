# Options Operations System
**Owner:** Raymond Davis  
**Mode:** Paper trading only  
**Instruments:** SPY · QQQ · Major ETFs  
**Strategy:** Weekly premium income + defined-risk entries  
**Date:** 2026-05-11

---

## Session Dashboard

```
╔══════════════════════════════════════════════════════════════════════╗
║                   OPTIONS OPERATIONS CENTER                          ║
╠══════════════════════════════════════╦═══════════════════════════════╣
║  WEEKLY CYCLE STATUS                 ║  CURRENT POSITIONS            ║
║  ─────────────────────────────────   ║  ──────────────────────────── ║
║  Cycle:  Week of May 11–16, 2026    ║  SPY:   No position           ║
║  DTE:    Focus → 5–21 DTE           ║  QQQ:   No position           ║
║  Exp:    This Friday / Next Friday  ║  IWM:   No position           ║
║                                      ║                               ║
║  Market Conditions:                  ║  OPEN P/L:  $0.00            ║
║  VIX Level:  --                      ║  PREMIUM COLLECTED:  $0.00   ║
║  VIX Trend:  --                      ║  REALIZED:  $0.00            ║
║  IV Rank:    --                      ║                               ║
╠══════════════════════════════════════╩═══════════════════════════════╣
║  RISK SNAPSHOT                                                       ║
║  Max Risk This Week: $200 (2% sim account)                          ║
║  Max Positions: 2 concurrent                                        ║
║  Undefined-risk trades: ❌ NOT PERMITTED                            ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Options Market Context

```
VIX REGIME → STRATEGY SELECTION
────────────────────────────────────────────────────────────
VIX < 15   │ LOW   │ Premium thin — reduce size, skip if <$0.50 credit
VIX 15–20  │ IDEAL │ Premium collection is optimal → full strategy menu
VIX 20–30  │ HIGH  │ Sell premium aggressively, manage early, wider strikes
VIX > 30   │ SPIKE │ No new premium sales — wait 1–2 days for stabilization
────────────────────────────────────────────────────────────

IV RANK (IVR) DECISION TREE:
  IVR > 50%  → Sell premium (favorable)
  IVR 30–50% → Sell if setup otherwise strong
  IVR < 30%  → Skip credit spreads — buy debit instead (directional play)
```

---

## Options Session Calendar

```
WEEKLY OPTIONS CYCLE
─────────────────────────────────────────────────────────────────────
 MON        TUE        WED        THU        FRI
  │          │          │          │          │
  │  Scan    │  Entry   │  Manage  │  Manage  │  Exit/expire
  │  Screen  │  Window  │  Monitor │  Monitor │  Review
  │          │          │          │          │
  ●──────────●──────────●──────────●──────────●
  
  MON: Pre-market scan → identify setups → review IV rank
  TUE: Primary entry day (full week premium intact, defined risk)
  WED: First management check (50% profit? → close early)
  THU: Urgent management (approaching expiry, roll or close)
  FRI: Expiration management — DO NOT hold through expiry blindly
  
  BEST ENTRY: Tuesday morning 30–60 min after open
  WHY: Monday noise settled, full premium week ahead, SPY direction clearer
```

---

## Setup Playbooks

### Setup A — Cash-Secured Put (CSP)

```
CRITERIA:
  ✓ Bullish or neutral market bias
  ✓ IVR > 40% (premium is rich)
  ✓ Strike at or below strong technical support
  ✓ Underlying I'm willing to own at that price
  ✓ Expiry: 7–21 DTE (sweet spot: 14 DTE)
  ✓ Min premium collected: $0.50/contract ($50) — no "lottery" premium

ENTRY:
  Sell PUT at strike = support level or delta 20–30
  Collect premium
  Secure full cash (or sim account equivalent)

MANAGEMENT:
  → Close at 50% max profit (don't get greedy)
  → Close if loss reaches 2× credit collected
  → Roll down and out if tested but still bullish

RISK/REWARD:
  Max profit: Premium collected
  Max loss: Strike price − premium (fully collateralized)
  Target: 50% profit capture, then close

SETUP CARD:
┌─────────────────────────────────────────────────────────────┐
│  SPY CASH-SECURED PUT (PAPER)                               │
│  ─────────────────────────────────────────────────────────  │
│  Entry: Sell SPY $XXX Put expiring [DATE]                  │
│  Strike: [Support level, delta 20–25]                      │
│  Premium: $[X.XX] per contract                             │
│  Breakeven: Strike − Premium                               │
│  Max Profit: $[X.XX] × 100 shares                          │
│  Max Loss: $[XXX.00] − premium (if to zero)                │
│  Close At: 50% profit target                               │
│  Stop: 2× credit loss → close                              │
└─────────────────────────────────────────────────────────────┘
```

### Setup B — Vertical Credit Spread (Bull Put Spread)

```
CRITERIA:
  ✓ Neutral to bullish bias
  ✓ IVR > 35%
  ✓ Short strike at technical support
  ✓ Long strike 5–10 points below (defined risk)
  ✓ Net credit ≥ 1/3 of spread width
  ✓ DTE: 7–21

EXAMPLE (SPY):
  Sell SPY 510P  (short put, near support)
  Buy  SPY 505P  (long put, protection)
  Net credit: ~$1.50–2.00 (target)
  Max profit: credit received
  Max loss: spread width − credit (e.g., $5.00 − $1.50 = $3.50)
  R:R: 1:2.3 — acceptable if win rate > 65%

MANAGEMENT:
  → Close at 50% profit
  → Close full spread if short strike breached (don't leg out)
  → No rolling undefined risk

PREFERRED:
  Bull Put Spread on SPY/QQQ during confirmed uptrend
  Bear Call Spread when bearish/overbought (mirror setup)
```

### Setup C — Iron Condor (Range-Bound Markets)

```
CRITERIA:
  ✓ VIX 16–22 (elevated but not spiking)
  ✓ Market in consolidation / no major trend
  ✓ Wide expected move → sell OUTSIDE the expected move
  ✓ Symmetric risk on both sides
  ✓ DTE: 21–30 (more time for theta to work)

CONSTRUCTION:
  Sell OTM Call + Buy further OTM Call (Bear Call Spread)
  Sell OTM Put  + Buy further OTM Put  (Bull Put Spread)

  Target: Underlying stays between short strikes

WINGS:
  SPY: Use ±2–3% from current price for short strikes
  Check 1 SD expected move on the options chain

MANAGEMENT:
  → Close at 25–35% of max profit (more conservative — two-sided risk)
  → If one side tested: close the tested side, leave other open
  → Never let one side go fully against you hoping for reversal

SIZING:
  Max 1 Iron Condor per name at a time
  Max $150 total risk per condor ($1,500 notional if $5 wide spreads)
```

### Setup D — Defined-Risk Directional (Debit Spread)

```
USE WHEN:
  ✓ Strong directional conviction (not neutral)
  ✓ IVR < 30% (buy spreads — premium is cheap)
  ✓ Upcoming catalyst (earnings not recommended — too binary)
  ✓ Technical breakout confirmed

CONSTRUCTION:
  Bull Call Spread: Buy ATM call, sell OTM call (same expiry)
  Bear Put Spread:  Buy ATM put, sell OTM put (same expiry)

SIZING:
  Risk exactly what you'd risk on a CSP
  Debit paid = max loss — size accordingly

TARGET:
  50–75% of max profit
  DTE: 14–30 (don't buy <14 DTE debit spreads — theta kills it)
```

---

## Premium Income Tracker

```
╔══════════════════════════════════════════════════════════════╗
║              WEEKLY PREMIUM COLLECTION LOG                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Week:  ___________                                          ║
║                                                              ║
║  POSITIONS OPENED THIS WEEK:                                 ║
║  ┌──────┬──────┬───────┬──────┬────────┬────────┬────────┐  ║
║  │Symbol│Setup │Strike │DTE   │Premium │Status  │P/L     │  ║
║  ├──────┼──────┼───────┼──────┼────────┼────────┼────────┤  ║
║  │      │      │       │      │        │        │        │  ║
║  │      │      │       │      │        │        │        │  ║
║  └──────┴──────┴───────┴──────┴────────┴────────┴────────┘  ║
║                                                              ║
║  WEEKLY SUMMARY:                                             ║
║  Gross Premium:  $____    Realized P/L:  $____              ║
║  Contracts:  ___          Win Rate: ____%                    ║
║  Avg DTE at Entry: ___    Avg DTE at Close: ___             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  CUMULATIVE PERFORMANCE                                      ║
║  Total Trades:  0     Win Rate:  ---%                       ║
║  Premium Collected:  $0.00    Realized:  $0.00              ║
║  Avg Win:  $---    Avg Loss:  $---                          ║
║  Expected Value per Trade: $---                             ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Trade Journal Template

```
DATE: ___________  WEEK: ___________

INSTRUMENT:  ___________  (SPY / QQQ / IWM / Other)
SETUP TYPE:  A-CSP / B-Bull Put / C-Iron Condor / D-Debit Spread
DIRECTION:   Bullish / Bearish / Neutral

MARKET CONTEXT:
  VIX Level: ___   IVR: ___%   Market Trend: Up / Down / Sideways
  SPY trend (1W): ___________  Support: _______  Resistance: _______

POSITION DETAILS:
  Short leg:  _______ [Strike] _______ [Exp]  @ $[credit/debit]
  Long leg:   _______ [Strike] _______ [Exp]  @ $[credit/debit]
  Net:        $_______ credit / debit
  Contracts:  ___
  Max Profit: $_______ Max Risk: $_______

PRE-TRADE CHECKLIST:
  □ VIX / IVR checked and setup criteria met
  □ Strike below / above clear technical level
  □ No earnings within DTE window
  □ No scheduled FOMC/CPI near expiry
  □ R:R acceptable (credit ≥ 1/3 spread for credits)
  □ Position size ≤ 2% account risk
  □ Max 2 concurrent positions rule: ___/2

MANAGEMENT PLAN:
  Profit target: Close at ___% profit = $_______ credit
  Stop loss: Close if loss reaches $_______ (2× credit)
  Roll trigger: ___________

RESULT:
  Closed on: _______  P/L: +/- $_______
  Outcome: Full Profit / Partial / Loss / Rolled / Expired Worthless

POST-TRADE:
  Did I follow the plan? Yes / No
  Management error? ___________
  Market reading: Correct / Off on direction / Off on timing
  Note for improvement: ___________
```

---

## Risk Management Rules (Options-Specific)

| Rule | Limit |
|---|---|
| Max risk per trade | 2% sim account ($200) |
| Max concurrent positions | 2 |
| Undefined-risk trades | ❌ Never (no naked puts/calls) |
| Min premium (credit trades) | $0.50/contract |
| Close at profit target | 50% of max profit |
| Stop loss | 2× credit collected |
| Earnings rule | No positions through earnings |
| FOMC/CPI rule | Close or hedge before major macro events |
| Roll rule | Only roll if thesis still intact |

---

## Options-Specific Market Calendar Checks

| Event | Action |
|---|---|
| Earnings within DTE | Skip — too binary, IV crush unpredictable |
| FOMC meeting | Close position day before or size to 50% |
| CPI release | Monitor — may spike VIX; manage accordingly |
| VIX > 30 sudden spike | Close all credit spreads at market — protect capital |
| VIX < 12 | Reduce size — premium not worth the risk |

---

## Transition Criteria (Paper → Live)

- Minimum 12 completed weekly cycles (paper)
- Win rate ≥ 58% on credit trades
- Zero undefined-risk losses
- Consistent $50–$150 simulated premium/week
- Journal complete for all 12 cycles
- No panic-close or plan deviation in last 4 cycles
