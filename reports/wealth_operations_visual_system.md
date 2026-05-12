# Wealth Operations Visual Design System
**Owner:** Raymond Davis  
**Scope:** All Nexus Personal Wealth Operations reports and dashboards  
**Aesthetic:** Apple/Atlas — clean, modern, premium, high-signal  
**Date:** 2026-05-11

---

## Design Philosophy

```
CORE PRINCIPLES
════════════════════════════════════════════════════════════════════

1. HIGH SIGNAL / LOW NOISE
   Every element earns its place.
   No decorative borders, no repeated labels, no filler text.
   If it doesn't help you make a decision, it doesn't appear.

2. OPERATIONAL CLARITY
   A 2-second read should answer: "What do I do next?"
   Status → context → action. Always in that order.

3. PREMIUM WITHOUT DECORATION
   Clean whitespace is a feature.
   Wide ASCII borders only when they organize information.
   Thin separators (─) over thick (═) except for system-level framing.

4. CONSISTENT VOCABULARY
   Wins = green signal → use ✅
   Warnings = ⚠️
   Hard stops = ❌
   Pending = □
   Complete = ■ or ✓
   Star rating = ⭐ (discipline scores only)

5. MOBILE-FIRST READABILITY
   All ASCII dashboards readable on iPhone screen (Telegram)
   Max line width: 50–60 chars for Telegram, 72 for reports
```

---

## Color Vocabulary (ASCII Equivalent)

```
TEXT ENCODING SYSTEM
════════════════════════════════════════════════════════════════════

SIGNAL     │ ASCII Representation       │ Usage
───────────┼────────────────────────────┼────────────────────────────
CRITICAL   │ ❌  [HARD STOP]            │ Rule violations, limits hit
CAUTION    │ ⚠️  [MONITOR]              │ Approaching limits
GOOD       │ ✅  [OK / SAFE]            │ System health, compliance
PENDING    │ □   [TO DO]                │ Checklists, milestones
COMPLETE   │ ■   [DONE]                 │ Completed items
FOCUS      │ ▶   [ACTIVE]               │ Currently watching
PROGRESS   │ ████░░░░  [PROGRESS BAR]   │ Completion %, trade progress
SEPARATOR  │ ─   [LIGHT DIVIDER]        │ Section breaks within panels
FRAME      │ ═   [HEAVY FRAME]          │ Top-level system boundaries
ARROW      │ →   [NEXT STEP]            │ Decision flow, routing
```

---

## Panel Templates

### Level 1 — System Frame (Full Dashboard)

```
╔══════════════════════════════════════════════════════════════════════╗
║                    [SYSTEM NAME]                                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  [Primary status row — most important fact first]                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  [Secondary data]                                                    ║
╚══════════════════════════════════════════════════════════════════════╝

Rule: Level 1 frames are used ONCE per report (the dashboard).
      All sub-sections use Level 2 or 3 patterns.
```

### Level 2 — Split Panel (Side by Side)

```
╠════════════════════╦═════════════════════════════════════════════════╣
║  LEFT TOPIC        ║  RIGHT TOPIC                                    ║
║  ────────────────  ║  ──────────────────────────────────────────────║
║  [data]            ║  [data]                                         ║
╠════════════════════╩═════════════════════════════════════════════════╣

Rule: Use 2-column split when two topics are always read together.
      Never 3+ columns — too cramped.
```

### Level 3 — Simple Card

```
┌─────────────────────────────────────┐
│  CARD TITLE                         │
│  ─────────────────────────────────  │
│  Field 1:  Value                    │
│  Field 2:  Value                    │
│  Field 3:  Value                    │
└─────────────────────────────────────┘

Rule: Setup cards, quick-reference items.
      Round corners (┌┐└┘) vs. double-line for visual hierarchy.
```

### Level 4 — Inline Checklist

```
PRE-TRADE CHECKLIST:
  □ Item one
  □ Item two
  ■ Item three (completed)
  ✅ Item four (system-confirmed)

Rule: No borders needed — whitespace + indentation is enough.
      Max 7 items per checklist. If more, split into groups.
```

### Level 5 — Metric Table

```
┌──────────────────┬────────┬──────────┬──────────┐
│ Metric           │ Value  │ Target   │ Status   │
├──────────────────┼────────┼──────────┼──────────┤
│ Win Rate         │  ---%  │  ≥55%   │ Pending  │
│ Expectancy       │  ---   │  > 0    │ Pending  │
└──────────────────┴────────┴──────────┴──────────┘

Rule: 3–4 columns max. Left-align labels. Right-align numbers.
```

---

## ASCII Progress Bar System

```
PROGRESS BAR ENCODING
════════════════════════════════════════════════════════════════════

  0%    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0/30 trades
  25%   ████████░░░░░░░░░░░░░░░░░░░░░░░░  7/30 trades
  50%   ████████████████░░░░░░░░░░░░░░░░  15/30 trades
  75%   ████████████████████████░░░░░░░░  23/30 trades
  100%  ████████████████████████████████  30/30 ✅

USAGE:
  Milestone completion → 32-char bar
  Daily session time → 20-char bar
  P/L toward target → 20-char bar
  Weekly progress → shown as X/Y not bar (more readable small)
```

---

## Session Timeline Template

```
SESSION TIMELINE (reusable across all time-based views)
════════════════════════════════════════════════════════════════════

 TIME    │ 4am   6am   8am   10am  12pm  2pm   4pm   6pm
         │  │     │     │     │     │     │     │     │
 FOREX   │  ░░░░░░░░████████████████▓▓▓▓▓▓▓▓░░░░░░│
 OPTIONS │                          ████████████░░░│
 AI BIZ  │        ──────────────────────────────────

 ████ = Primary execution window
 ▓▓▓▓ = Highest priority — full attention
 ░░░░ = Monitor / reduced size
 ──── = Any time — independent of market hours
```

---

## Telegram-Optimized Display Rules

```
TELEGRAM FORMATTING (≤700 chars target)
════════════════════════════════════════════════════════════════════

DO:
  ✅ Lead with the most critical fact
  ✅ Use → for next steps
  ✅ Use bullet structure (not nested tables)
  ✅ Include one concrete action per brief
  ✅ End with a clear focus statement

DON'T:
  ❌ ASCII frames wider than 50 chars (breaks mobile)
  ❌ More than 5 data points per Telegram message
  ❌ Repeat information already visible to the user
  ❌ Output raw JSON or logs
  ❌ Include detailed tables (they break in Telegram rendering)

TELEGRAM BRIEF TEMPLATE:
──────────────────────────────────────────────────────────────────
📊 [BRIEF TYPE] — [DATE]
─────────────────────
[2–3 critical data points]

SETUP: [what's forming]
ACTION: [one specific next step]
FOCUS: [today's priority in one sentence]
──────────────────────────────────────────────────────────────────
```

---

## Trade Setup Card System

```
STANDARDIZED SETUP CARD FORMAT
════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│  [INSTRUMENT] [DIRECTION] SETUP — [DATE]                    │
│  Setup Type: [A/B/C]    Session: [London/NY/Overlap]        │
│  ─────────────────────────────────────────────────────────  │
│  Price:   [current]                                         │
│  Range:   [support] – [resistance]                          │
│  Entry:   [price] ([method: limit/pullback/breakout])       │
│  Stop:    [price] ([-xx pips])                              │
│  T1:      [price] ([+xx pips] / [x.xR])                    │
│  T2:      [price] ([+xx pips] / [x.xR])   [optional]       │
│  ─────────────────────────────────────────────────────────  │
│  Risk:  $[amount] ([x%] of sim account)                     │
│  Lots:  [size]                                              │
│  Setup quality: ____%  Criteria met: ___/5                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Status Indicator Vocabulary

| Symbol | Meaning | When to Use |
|---|---|---|
| ✅ | Confirmed / Safe / Complete | System health, plan adherence, milestone reached |
| ⚠️ | Warning / Monitor | Approaching limits, elevated risk |
| ❌ | Hard stop / Not permitted | Rule violation, safety constraint |
| □ | Pending / To do | Checklist items |
| ■ | Done | Completed checklist items |
| ▶ | Active / Watching | Current watchlist focus |
| → | Next action | Decision flow, routing |
| ★ | Priority / Milestone | Key goals, first revenue event |
| ⭐ | Discipline rating | Score display only |
| ░ | Empty / Low | Progress bar background |
| █ | Filled / High | Progress bar fill |
| ▓ | Priority zone | Highest-value time window |

---

## Report Naming Convention

```
REPORT FILE NAMES
────────────────────────────────────────────────────────────────────

STATIC REFERENCE REPORTS:
  reports/[pillar]_operations_system.md         → playbooks + rules
  reports/[pillar]_operations_system.md         → e.g., forex_operations_system.md

OPERATIONAL FRAMEWORKS:
  reports/money_management_framework.md
  reports/daily_execution_engine.md
  reports/personal_ceo_dashboard.md
  reports/wealth_operations_visual_system.md

PLANNING + INTELLIGENCE:
  reports/tomorrow_execution_plan.md            → replaces daily
  reports/NEXUS_PERSONAL_WEALTH_OPERATIONS_MASTER_PLAN.md

LIVE JOURNAL ENTRIES (pattern — not yet created):
  reports/trade_journal/YYYYMMDD_forex.md
  reports/trade_journal/YYYYMMDD_options.md
  reports/trade_journal/YYYYMMDD_weekly_review.md
```
