# Mobile UX Refinement Report
**Date:** 2026-05-12  
**Phase:** B — Mobile UX + Gamified Motion

---

## Components Built

### MobileBottomNav.tsx (NEW)
Persistent bottom navigation bar for mobile.

- 5 tabs: Home, Trading, Funding, Inbox, Actions
- Active state: filled icon + blue label + #eef0fd background pill
- Plan-gated: Trading and Funding show as locked (grey) for free users
- `safe-area-bottom` padding for iPhone notch/home indicator
- `md:hidden` — only renders on mobile, desktop uses sidebar
- Wired into AppShell.tsx — all routes get it automatically
- Content area adds `pb-16 md:pb-0` to avoid overlap

### MobileTradingHUD.tsx (NEW)
Compact trading intelligence HUD for mobile dashboard.

- Balance + today % in single compact bar
- Animated circular risk gauge (SVG) — green/amber/red by risk %
- Open position counter (pill squares)
- Risk label badge (LOW / MODERATE / HIGH / CRITICAL)
- Mini trade cards: market, direction, pips P&L, TP progress bar
- Circuit breaker mode: full-width red alert instead of normal HUD
- "This week" stat pill at bottom
- PAPER MODE indicator always visible
- Props: `onExpand?: () => void` — tap-to-expand to full TradingDashboard

### AppShell.tsx (UPDATED)
- Added `MobileBottomNav` import and render
- Content scroll container: `pb-16 md:pb-0` (56px clearance for bottom nav)

---

## B1 — Dashboard Compression Status

Current `Dashboard.tsx` is 443 lines with glass-card components. Key mobile issues:
- Card padding is desktop-optimized (`p-5` / `p-6`)
- Journey steps section has excessive vertical spacing
- Roadmap steps could be horizontal scroll on mobile

Partial fix applied: `pb-16` on scroll container prevents bottom nav overlap.
Full Dashboard compression (card padding, mobile stacking order) is a follow-on task — recommend as next UX sprint.

---

## B4 — Motion Polish Status

Framer Motion is available in the project (`package.json` dependency confirmed).
Key components with animation opportunities:
- P&L numbers: count-up on value change (`useSpring`)  
- Strategy cards: slide-in on mount (`initial: {opacity:0, y:8}`)
- Risk gauge: SVG stroke animation already uses CSS transition
- TP progress bars: CSS transition-all already applied

Framer Motion integration deferred to next UX pass — core layout + navigation completed first per mobile-first priority.

---

## B5 — PWA Validation

PWA status (from prior validation pass):
- Service worker: registered via Vite PWA plugin
- Manifest: `nexuslive/public/manifest.json` present
- Install prompt: `InstallPrompt.tsx` component active
- Icons: verified in prior pass
- Test plan: Install on iPhone via Safari share → Add to Home Screen

Confirmed no regressions from this pass — AppShell changes preserve PWA behavior.

---

## Known Gaps (Next Mobile Sprint)

- [ ] Dashboard card padding: reduce `p-5` → `p-4` on `sm:` breakpoint
- [ ] Roadmap: horizontal scroll on mobile
- [ ] Journey steps: collapse after completion on mobile
- [ ] Framer Motion count-up on P&L numbers
- [ ] Swipe gesture on Paper Trading Arena trade cards
- [ ] Trading HUD: wire to real Supabase data (currently mock)
