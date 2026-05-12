# Mobile Trading HUD Refinement — Report
**Date:** 2026-05-12 | **Pass:** Trading Demo Platform | **Safety:** Paper mode only

## Changes Made

### Framer Motion v12 Integration
`MobileTradingHUD.tsx` updated to use `motion/react` (v12 package name):

```typescript
import { motion, AnimatePresence } from 'motion/react';
```

### Animated Elements
| Element | Animation | Duration |
|---|---|---|
| HUD container | fade-in + slide up (y: 8→0) | 300ms |
| Paper balance | opacity fade-in with 100ms delay | 200ms |
| SVG risk gauge stroke | strokeDashoffset ease-out | 800ms |
| Trade slot bars | scaleY from 0 staggered per-bar | 80ms gap |
| MiniTradeCard entry | opacity + slide | 250ms |
| TP progress bar | width 0→N% ease-out | 500ms |
| AnimatedPnL | count-up cubic ease (rAF) | 600ms |
| Circuit breaker card | scale 0.97→1 | 200ms |
| AnimatePresence | trades list swap mode=popLayout | — |
| Week stat pill | opacity fade with 200ms delay | — |

### SVG Risk Gauge
Uses `strokeDashoffset` animation for smooth arc fill. Math:
- R = 14, circumference = 2πR ≈ 87.96
- `strokeDashoffset = CIRC - (riskUsedPct/100 * CIRC)`
- Color: green (≤60%), amber (61–80%), red (>80%)

### AnimatedPnL Counter
requestAnimationFrame count-up from 0 to final pip value in 600ms using cubic ease-out `1 - (1-t)³`. Recreates on prop change via useEffect dependency.

## Mobile UX Improvements
- `active:scale-[0.99]` on HUD bar for tap feedback
- Circuit breaker card shows scale-in entry animation
- Empty state (no trades) animates in/out with AnimatePresence

## Safety
All data sourced from MOCK_METRICS/MOCK_TRADES constants. No live API calls from this component. PAPER MODE badge always visible.
