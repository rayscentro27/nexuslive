# Money Management Framework
**Owner:** Raymond Davis  
**Mode:** Paper trading + simulation  
**Scope:** All four operational pillars  
**Date:** 2026-05-11

---

## Capital Allocation Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                NEXUS CAPITAL ALLOCATION FRAMEWORK                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   TOTAL SIM ACCOUNT: $10,000 (paper trading baseline)               ║
║                                                                      ║
║   ┌─────────────────────────────────────────────────────────────┐   ║
║   │  PILLAR ALLOCATION                                          │   ║
║   │                                                             │   ║
║   │  Forex (EUR/USD, GBP/USD, XAU/USD)    30% → $3,000        │   ║
║   │  ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │   ║
║   │                                                             │   ║
║   │  Options (SPY/QQQ, premium income)     30% → $3,000        │   ║
║   │  ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │   ║
║   │                                                             │   ║
║   │  Crypto (BTC/ETH + AI narratives)      20% → $2,000        │   ║
║   │  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │   ║
║   │                                                             │   ║
║   │  AI Business (real capital reserve)    20% → $2,000        │   ║
║   │  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │   ║
║   └─────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Risk Cap Matrix

```
RISK CAP TABLE — ALL PILLARS
════════════════════════════════════════════════════════════════════

┌───────────────────────┬────────────────┬───────────┬───────────┐
│ Rule                  │ Forex          │ Options   │ Crypto    │
├───────────────────────┼────────────────┼───────────┼───────────┤
│ Max risk per trade    │ 1% = $100      │ 2% = $200 │ 5% = $100 │
│ Max trades per day    │ 3              │ 1         │ N/A (swing│
│ Daily loss limit      │ 2% = $200      │ 4% = $400 │ 10% = $200│
│ Weekly loss limit     │ 4% = $400      │ 6% = $600 │ 15% = $300│
│ Max concurrent pos.   │ 2 pairs        │ 2 spreads │ 4 tokens  │
│ Leverage allowed      │ None (1:1 sim) │ None      │ None      │
│ Undefined risk        │ N/A            │ ❌ Never  │ N/A       │
│ Stop after daily limit│ ✅ HARD STOP   │ ✅ HARD   │ ✅ HARD   │
└───────────────────────┴────────────────┴───────────┴───────────┘

HARD STOP RULE:
  Any pillar that hits its daily loss limit → close platform
  Weekly limit hit → pause pillar, review setup criteria before returning
  Two consecutive weekly losses → mandatory rest week, no new entries
```

---

## Position Sizing Calculator

```
FOREX POSITION SIZING
──────────────────────────────────────────────────────────────────
  Formula: Lots = (Account × Risk%) ÷ (Stop × Pip Value)

  Account: $10,000   Risk: 1% = $100   Pip value (EUR/USD): $10/pip

  STOP PIPS  │  POSITION SIZE (Lots)  │  RISK
  ──────────┼────────────────────────┼─────────
  10 pips   │  1.00 lot              │  $100
  15 pips   │  0.67 lots             │  $100
  20 pips   │  0.50 lots             │  $100
  25 pips   │  0.40 lots             │  $100
  30 pips   │  0.33 lots             │  $100
  50 pips   │  0.20 lots             │  $100

  XAU/USD adjustment: pip value ~$10/0.1 lot → size accordingly
  GBP/USD: pip value approximately = EUR/USD at current rates

OPTIONS POSITION SIZING
──────────────────────────────────────────────────────────────────
  Max risk = 2% = $200 per position

  SPREAD WIDTH  │  MAX CONTRACTS  │  MAX RISK
  ─────────────┼─────────────────┼──────────
  $1 wide       │  2 contracts    │  $200
  $2 wide       │  2 contracts    │  $400 → NO, too much
  $5 wide       │  1 contract     │  $500 → NO, too much
  $5 wide credit│  1 if net > $2  │  $300 max risk → OK with $500 account

  RULE: Never let max risk exceed 2% of sim account in options

CRYPTO POSITION SIZING
──────────────────────────────────────────────────────────────────
  BTC/ETH (core): DCA amounts — $100–$200 per entry (paper)
  AI tokens (Tier 1): Max 5% of sim portfolio = $100 (paper)
  AI tokens (Tier 2/3): Max 2% = $40 (paper) — small speculative
```

---

## Drawdown Management Protocol

```
DRAWDOWN RESPONSE MATRIX
════════════════════════════════════════════════════════════════════

TIER 1 — MINOR DRAWDOWN (5–10% from peak)
  Action: Continue with full system, review setup quality
  Mindset: Normal — part of trading
  Change: None to strategy

TIER 2 — MODERATE DRAWDOWN (10–15% from peak)
  Action: Reduce position size to 50% of normal
  Mindset: System under stress — protect capital
  Change: Tighten setup criteria — only A+ setups
  Journal: Write drawdown review entry

TIER 3 — SIGNIFICANT DRAWDOWN (15–20% from peak)
  Action: Pause all new entries for 1 week
  Mindset: Re-evaluate — is the setup failing?
  Change: Review all recent losses — identify pattern
  Journal: Full system audit entry required

TIER 4 — CRITICAL DRAWDOWN (>20% from peak)
  Action: Full system pause for 2+ weeks
  Mindset: Something is broken — find it
  Change: Do not resume until root cause identified
  External: Consider seeking feedback on strategy
  
  NO EXCEPTIONS: Do not "trade your way out" of drawdown
  Capital preservation > recouping losses quickly
```

---

## Sim-to-Live Transition Framework

```
LIVE CAPITAL UNLOCK CRITERIA — PER PILLAR
════════════════════════════════════════════════════════════════════

FOREX UNLOCK (all must be true):
  □ 30+ paper trades completed
  □ Win rate ≥ 55% over last 20 trades
  □ Positive expectancy: (Win% × Avg win) − (Loss% × Avg loss) > 0
  □ No plan violations in last 10 trades (discipline = 100%)
  □ Drawdown never exceeded 10% of sim account in any 4-week period
  □ Setup criteria followed without exception for 4+ consecutive weeks

OPTIONS UNLOCK (all must be true):
  □ 12+ weekly premium cycles completed
  □ No undefined-risk positions taken
  □ Win rate ≥ 60% on credit trades
  □ Consistent $50–$150 weekly premium in simulation
  □ Successfully managed 2+ positions (early close, roll, loss stop)

CRYPTO UNLOCK (all must be true):
  □ 3-month conviction journal completed
  □ 2+ AI narrative calls correct BEFORE price movement (documented)
  □ On-chain review checklist completed weekly for 12+ weeks
  □ No panic-close in simulated drawdown > 20%

AI BUSINESS UNLOCK:
  ✅ Already live — first revenue event = criteria met
  Scale investment of time/money after first $500 MRR

LIVE CAPITAL SIZING (when unlocked):
  Start at 25% of intended allocation
  Scale to 50% after 30 additional live trades (no drawdown >10%)
  Full allocation only after demonstrating sim performance holds live
```

---

## Cross-Pillar Correlation Monitor

```
MARKET CONDITION MATRIX → PILLAR PRIORITY
═════════════════════════════════════════════════════════════════════

                    RISK-ON        RISK-OFF       VOLATILE
                    Market         Market         VIX spike
Forex              ███ Active      ███ Active     ██ Reduced
Options (premium)  ██ Monitor      ████ Prime     ████ Prime
Options (debit)    ████ Prime      ██ Monitor     ██ Monitor
Crypto (BTC/ETH)   ████ Prime      ██ Reduce      ██ Reduce
Crypto (AI tokens) ████ Active     █ Hold only    █ Hold only
AI Business        ████ Always     ████ Always    ████ Always

DXY (Dollar) IMPACT:
  DXY Rising  → Forex USD pairs favor USD strength
             → Gold (XAU) bearish pressure
             → Crypto headwind
             → Options: SPY may be under pressure
  DXY Falling → Opposite of above
  
RULE: When in doubt — AI Business ops are always the priority.
      Trading is skill-building. AI Business is income-building.
```

---

## Monthly Review Protocol

```
MONTHLY MONEY MANAGEMENT REVIEW CHECKLIST
─────────────────────────────────────────────────────────────────

PERFORMANCE:
  □ Total sim P/L vs. starting balance
  □ Each pillar P/L tracked separately
  □ Win rate per pillar vs. targets
  □ Biggest win — was it planned?
  □ Biggest loss — was it preventable?

DISCIPLINE:
  □ Plan-following rate (target: ≥90%)
  □ Skipped bad setups count (quality over quantity)
  □ Emotional overrides (target: 0)
  □ Stop loss violations (target: 0)

CAPITAL EFFICIENCY:
  □ Drawdown peak this month
  □ Recovery time from drawdowns
  □ % of days with zero trades (patience discipline)
  □ Avg R:R on closed trades

AI BUSINESS:
  □ Opportunities scored this month
  □ Outreach actions taken
  □ Revenue events (any amount)
  □ Skills/knowledge added

NEXT MONTH:
  □ Any adjustments to setup criteria?
  □ Any pillar to pause or increase focus?
  □ Next unlock milestone approaching?
  □ Capital re-allocation needed?
```
