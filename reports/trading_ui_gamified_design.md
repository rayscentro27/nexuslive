# Nexus Trading Intelligence Platform — Gamified Motion UI Design
**Date:** 2026-05-12  
**Mode:** Design specification — paper trading only, TRADING_LIVE_EXECUTION_ENABLED=false

---

## Design Philosophy

The Nexus trading UI must feel like a mission control room that you also want to live in. Not a Bloomberg terminal clone. Not a crypto casino. An AI-supervised trading intelligence cockpit — calm under pressure, alive with data, beautiful under all conditions.

**Three emotional targets:**
1. **Confidence** — operator feels in control, not overwhelmed
2. **Momentum** — platform feels alive, responsive, forward-moving
3. **Clarity** — every number has context, every action has consequence

---

## Visual Identity

### Color System
```
Background deep:    #0a0b14  (near-black blue)
Background surface: #0f1120  (card surfaces)
Background raised:  #151829  (elevated panels)
Border subtle:      #1e2240  (soft dividers)
Border active:      #3d5af1  (active elements)

Primary blue:       #3d5af1  (actions, primary)
Accent cyan:        #00d4ff  (live indicators, pulse)
Accent green:       #22c55e  (profit, confirmed, safe)
Accent amber:       #f59e0b  (warning, pending)
Accent red:         #ef4444  (loss, danger, circuit breaker)
Accent purple:      #8b5cf6  (AI elements, analysis)

Text primary:       #e8eaf6  (main content)
Text secondary:     #8b8fa8  (labels, metadata)
Text dim:           #4a4e6a  (inactive, placeholder)
```

### Typography
```
Display:   Inter 800 — hero numbers, P&L, strategy names
Label:     Inter 600 — section headers, card titles  
Body:      Inter 400 — descriptions, metadata
Mono:      JetBrains Mono — prices, timestamps, trade IDs
```

### Motion Principles
- **Entrance:** Elements slide + fade in on mount (200ms ease-out)
- **Live data:** Numbers count-up when values change
- **Alerts:** Pulse ring expands on new events, fades out
- **P&L positive:** Number flashes green briefly, then settles
- **P&L negative:** Number flashes red briefly, then settles
- **Loading:** Skeleton shimmer (not spinners)
- **Transitions:** Route changes use shared-element transitions

---

## Dashboard Pages

### 1. Trading Overview (Home)
```
┌─────────────────────────────────────────────────────┐
│  ⚡ NEXUS TRADING INTELLIGENCE          [PAPER MODE] │
│─────────────────────────────────────────────────────│
│                                                      │
│  TODAY'S P&L          ACTIVE STRATEGIES  WIN STREAK │
│  +$2,847  ↑2.1%           3 / 7          🔥 4 days │
│  [green pulse]        [blue glow]         [amber]   │
│                                                      │
│  ─────── AI PULSE ──────────────────────────────── │
│  ● London breakout scanning... (qwen3:8b)           │
│  ● Risk engine: nominal                             │
│  ● Next session: NY open in 2h 14m                 │
│                                                      │
│  ─────── LIVE PAPER TRADES ─────────────────────── │
│  EUR/USD  LONG   +28 pips  ████░░░░  TP: 40        │
│  GBP/JPY  SHORT  -12 pips  ░░░████  SL: 20        │
│                                                      │
│  [Strategy Registry] [Backtest] [Risk Center]       │
└─────────────────────────────────────────────────────┘
```

### 2. Strategy Cards (Registry)
```
┌─────────────────────────────────────────────────────┐
│  LONDON BREAKOUT v2.1           [ACTIVE] [PAPER]    │
│─────────────────────────────────────────────────────│
│  Market: EUR/USD  TF: 15m  Session: London          │
│                                                      │
│  Win Rate  ████████░░  71%   Drawdown  ░░░██  8%   │
│  AI Conf.  ███████░░░  68%   P.Factor  2.3x        │
│                                                      │
│  🏆 Rank #1 this week  📈 +4 streak  ⚡ Edge: HIGH  │
│                                                      │
│  [Run Backtest] [Paper Trade] [Request Approval]    │
└─────────────────────────────────────────────────────┘
```

### 3. Risk Gauge (Control Center)
```
         ACCOUNT HEALTH
    ┌────────────────────┐
    │    ████████░░░░    │  72% — NOMINAL
    │                    │
    │  Daily Risk: 1.2%  │  ← of 2% max
    │  Weekly:     3.1%  │  ← of 5% max
    │  Open Pos:   2     │  ← of 4 max
    │                    │
    │  ⚡ All clear      │
    └────────────────────┘
```

### 4. Session Heatmap
```
         EUR/USD WIN RATE BY SESSION + HOUR
    00 01 02 03 04 05 06 07 08 09 10 11 12
    ░░ ░░ ░░ ░░ ░░ ██ ██ ██ ██ ██ ░░ ░░ ░░  (London)
    ░░ ░░ ░░ ░░ ░░ ░░ ░░ ░░ ██ ██ ██ ██ ██  (NY overlap)

    ██ = >65% win rate   ░░ = <45%   moderate = between
```

---

## Animation Catalog

### Live Pulse (AI worker active)
```css
@keyframes pulse-ring {
  0%   { transform: scale(1);    opacity: 0.8; }
  70%  { transform: scale(1.8);  opacity: 0;   }
  100% { transform: scale(1.8);  opacity: 0;   }
}
```

### P&L Counter (number animates on change)
- Framer Motion `useSpring` from old value to new
- Green: value went up, Red: value went down
- Settles to neutral after 1.5s

### Trade Execution Flow
```
Signal detected → [flash blue] → Risk check → [flash amber]
→ Approved → [flash green] → Order placed → [pulse ring]
→ Position open → [steady glow]
```

### Confidence Bar
- Animated width fill on mount (600ms ease-out)
- Glow intensity proportional to confidence
- Pulses when AI re-evaluates

---

## Mobile Layout (iPhone)

```
┌──────────────────┐
│ ⚡ Nexus Trading  │
│ [P] PAPER MODE   │
├──────────────────┤
│  TODAY           │
│  +$1,247 ↑0.9%  │
│  ████████░░ 72%  │
├──────────────────┤
│  2 ACTIVE TRADES │
│  EUR/USD +18p 🟢 │
│  GBP/USD  -4p 🔴 │
├──────────────────┤
│ [swipe for risk] │
├──────────────────┤
│ 🏠 📊 ⚡ 🛡️ 💬 │
└──────────────────┘
```

Bottom nav: Overview / Strategy / AI / Risk / Hermes

---

## Gamification Elements

### Operator Levels
- INITIATE → ANALYST → STRATEGIST → EXECUTOR → COMMANDER
- XP earned from: consistent paper trading, strategy approvals, profitable sessions
- Level badge visible on profile and dashboard header

### Performance Streaks
- Win streak: 🔥 fire badge, grows with consecutive profitable sessions
- Session streak: calendar heatmap showing consistency
- Backtest streak: completing analysis sessions

### Strategy Competition
- Strategies ranked by paper trading performance this week
- Rank badge: 🥇 🥈 🥉 for top 3
- Movement arrows: ↑ improved, ↓ declined, → stable

### Milestone Cards
- "First profitable week" → unlocks advanced analytics
- "10-day paper streak" → unlocks session intelligence tab
- "Strategy approval" → unlocks guarded execution architecture
