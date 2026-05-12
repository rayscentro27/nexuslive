# Daily Execution Engine
**Owner:** Raymond Davis  
**Mode:** Paper trading + AI Opportunity pursuit  
**Scope:** All four operational pillars  
**Date:** 2026-05-11

---

## Daily Operating System

```
╔══════════════════════════════════════════════════════════════════════╗
║                    DAILY EXECUTION ENGINE                            ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             ║
║   │  MORNING     │  │  EXECUTION   │  │  EVENING     │             ║
║   │  BRIEF       │  │  WINDOW      │  │  RECAP       │             ║
║   │  7:00–8:00am │  │  9:30am–4pm  │  │  4:00–5:00pm │             ║
║   │  Context     │  │  Markets     │  │  Journal     │             ║
║   │  + Setup scan│  │  + AI Ops    │  │  + Plan      │             ║
║   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             ║
║          │                 │                  │                      ║
║          └─────────────────┴──────────────────┘                     ║
║                            │                                         ║
║              ┌─────────────▼──────────────┐                         ║
║              │   DISCIPLINE SCORE (daily)  │                         ║
║              │   Did you follow the plan?  │                         ║
║              └─────────────────────────────┘                         ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Morning Brief Protocol (7:00–8:00am EST)

```
PHASE 1: CONTEXT LOAD (7:00–7:20am)
──────────────────────────────────────────────────────────────────────
  □ Check Hermes Telegram morning brief
    → "good morning" → triggers daily briefing
    → Review overnight alerts, macro context
    
  □ Macro environment (2 min scan):
    DXY: _______ trend: Up / Down / Flat
    SPY: _______ pre-market: +/- _____%
    VIX: _______ regime: Low / Ideal / High / Spike
    BTC: _______ 24h: +/- _____%
    
  □ Economic calendar (check once):
    → Any CPI, FOMC, NFP, or major events today?
    → Mark event times — no trades 30 min before/after

PHASE 2: FOREX SETUP SCAN (7:20–7:40am)
──────────────────────────────────────────────────────────────────────
  EUR/USD:
    Current: _______  Overnight range: _______ – _______
    Key levels: Support: _______  Resistance: _______
    Setup forming? Yes / No / Monitor
    
  GBP/USD:
    Current: _______  Overnight range: _______ – _______
    Key levels: Support: _______  Resistance: _______
    Setup forming? Yes / No / Monitor
    
  XAU/USD:
    Current: _______  DXY correlation: Inverse active? Yes / No
    Key levels: _______ – _______
    Setup forming? Yes / No / Monitor

  FOREX DECISION: Trade today? Yes / No / Monitor only
  Setup type if yes: A / B / C  Setup criteria met? ____%

PHASE 3: OPTIONS SETUP SCAN (7:40–7:55am)
──────────────────────────────────────────────────────────────────────
  SPY:     Current: _______  IVR: ___%  VIX: _______
  QQQ:     Current: _______  IVR: ___%
  
  Options decision: New position today? Yes / No
    If yes: Setup type: CSP / Bull Put / Iron Condor / Debit Spread
    Strike target: _______  DTE: _______  Premium target: $_______
    Entry window: After 10am (avoid first 30 min open)

PHASE 4: KNOWLEDGE + AI OPPORTUNITY CHECK (7:55–8:00am)
──────────────────────────────────────────────────────────────────────
  □ Any new knowledge emails received? Ask Hermes: "what knowledge arrived?"
  □ Any funding/grant opportunities to review?
  □ AI opportunity from yesterday that needs follow-up?
  □ One concrete AI business action planned for today: ___________
```

---

## Primary Execution Window (9:30am–4:00pm EST)

```
TIME BLOCK SCHEDULE
═════════════════════════════════════════════════════════════════════

9:00–9:30am  │ OPTIONS ENTRY WINDOW
             │ Review pre-open setup, confirm VIX + IVR
             │ Wait 30 min after open before any options entry
             │ Enter if setup confirmed — limit order, not market

9:30–10:00am │ MARKET OPEN OBSERVATION
             │ Watch volatility settle — do NOT trade Forex in first 30 min
             │ Note opening direction for continuation bias
             │ No action unless setup was pre-planned

10:00–12:00pm│ PRIMARY FOREX WINDOW (London/NY Overlap)
             │ This is the highest-probability execution window
             │ Execute pre-planned setups only — no impulsive entries
             │ Monitor open positions — manage if needed
             │ AI Business: work on primary action item for today

12:00–12:30pm│ MIDDAY REVIEW (5 min)
             │ □ Open positions: protect profits if applicable
             │ □ Any positions approaching stop? Manage or hold per plan
             │ □ Market trend holding or reversing?

12:30–2:00pm │ AI BUSINESS OPERATIONS BLOCK
             │ DEDICATED AI OPPORTUNITY WORK (no market distraction)
             │ → Prospect outreach, proposal writing, product building
             │ → Knowledge ingestion review (if new intake arrived)
             │ → Grant research if applicable

2:00–3:00pm  │ NY SESSION MONITORING
             │ Monitor open Forex/Options positions
             │ No new Forex entries after 2pm (London closed)
             │ Options: Check if 50% profit target reached → close

3:00–3:45pm  │ AI BUSINESS + KNOWLEDGE BLOCK
             │ Continue AI opportunity work
             │ Review any daytime Hermes alerts

3:45–4:00pm  │ POSITION WRAP
             │ Close any same-day Forex positions if not at target
             │ Options: Note open positions, set alerts
             │ Save journal notes for evening recap
```

---

## Evening Recap Protocol (4:00–5:00pm EST)

```
PHASE 1: TRADING RECAP (4:00–4:20pm)
──────────────────────────────────────────────────────────────────────
  FOREX JOURNAL (for any trades taken):
    □ Fill trade journal template (reports/forex_operations_system.md)
    □ Did I follow the plan? Yes / No
    □ Pips result: +/- _____
    □ Setup quality rating: 1–5
    □ Emotional state during trade: Calm / Anxious / Overconfident
    
  OPTIONS JOURNAL (for any positions opened/closed):
    □ Fill options trade journal
    □ Premium captured vs. target
    □ Management decision quality

  DAILY DISCIPLINE SCORE:
    Plan-following rate:      ___%   (target ≥ 90%)
    Emotional overrides:      ___    (target: 0)
    Setups passed correctly:  ___    (rewarded with discipline score)

PHASE 2: AI BUSINESS RECAP (4:20–4:40pm)
──────────────────────────────────────────────────────────────────────
  □ AI opportunity action completed today? Yes / No → What?
  □ Any new leads or opportunities identified?
  □ Score any new opportunities with the scorecard
  □ Pipeline update — did any opportunity advance or close?

PHASE 3: TOMORROW PLANNING (4:40–5:00pm)
──────────────────────────────────────────────────────────────────────
  Economic calendar check for tomorrow:
    Major events: _____________  Time: _____________

  Forex focus for tomorrow:
    Key level to watch: ___________
    Setup criteria needed: ___________

  Options: Any positions to monitor or close tomorrow?
  
  AI Business priority action tomorrow: ___________
  
  Hermes message (end of day):
    → "day recap: [brief summary]" for Hermes context
```

---

## Discipline Scorecard

```
DAILY DISCIPLINE TRACKER
════════════════════════════════════════════════════════════════════

DATE: ___________

FOREX DISCIPLINE:
  Followed entry criteria exactly?          Yes / No  (1 pt)
  Position sized correctly?                 Yes / No  (1 pt)
  Used stop loss as planned?                Yes / No  (1 pt)
  Exited at planned level (not emotion)?    Yes / No  (1 pt)
  Skipped low-quality setup?                Yes / No  (1 pt)
  FOREX SCORE: ___/5

OPTIONS DISCIPLINE:
  Waited for setup criteria before entry?   Yes / No  (1 pt)
  Closed at 50% profit target (not held)?   Yes / No  (1 pt)
  No undefined-risk positions?              Yes / No  (1 pt)
  No earnings-week entries?                 Yes / No  (1 pt)
  OPTIONS SCORE: ___/4

GENERAL DISCIPLINE:
  Morning brief completed?                  Yes / No  (1 pt)
  No revenge trading or overtrading?        Yes / No  (1 pt)
  AI business action completed?             Yes / No  (1 pt)
  Journal filled out?                       Yes / No  (1 pt)
  GENERAL SCORE: ___/4

TOTAL DAILY SCORE: ___/13    %: ____%

WEEKLY TREND:
  Mon: ___/13   Tue: ___/13   Wed: ___/13   Thu: ___/13   Fri: ___/13
  Weekly avg: _____%   (Target: ≥ 85%)
```

---

## Weekly Operating Rhythm

| Day | Priority |
|---|---|
| **Monday** | Morning scan, options cycle check, AI biz plan for week |
| **Tuesday** | Primary options entry day, full Forex watchlist |
| **Wednesday** | First options management check (50%?), Forex active |
| **Thursday** | Close or roll any maturing options, Forex active |
| **Friday** | Options expiry management, Forex wind-down by noon |
| **Weekend** | Weekly review, next week planning, knowledge intake review |

---

## Weekly Review Template

```
WEEKLY REVIEW — Week of ___________

TRADING PERFORMANCE:
  Forex:   Trades ___  W/L ___/___  Net pips +/-___  P/L: $___
  Options: Trades ___  W/L ___/___  Premium: $___   P/L: $___
  Crypto:  Any changes? ______  Narrative score updates: ______

DISCIPLINE:
  Avg daily discipline score: _____%
  Plan violations: ___ (describe: _________________________)
  Best trade of the week: _________________________________
  Biggest mistake: ________________________________________

AI BUSINESS:
  Opportunities advanced: ___
  Outreach contacts made: ___
  Revenue events: $___
  Key learning: ___________

NEXT WEEK FOCUS:
  Primary trading focus: ___________
  AI business primary action: ___________
  Any system changes to implement? ___________
```
