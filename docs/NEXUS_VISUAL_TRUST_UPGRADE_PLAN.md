# Nexus Visual Trust Upgrade Plan

**Created:** 2026-05-18  
**Status:** 3 subtasks queued — claude_code + qa_worker assigned  
**Goal:** Make Nexus feel premium, alive, and trustworthy before client launch

---

## Current Issues (Audit Findings)

### Homepage
- Header hierarchy weak — nothing commanding attention above the fold
- CTA button not prominent enough (small, low contrast)
- No social proof visible without scrolling
- Feature icons too small, text-heavy sections
- No "alive" indicator (no real-time data, no animation)

### Admin Dashboard
- Too much content visible at once — overwhelming
- Bottom dock scrolls horizontally on mobile — hard to use
- No visual priority differentiation between critical and routine info
- Workforce visualization exists but not prominent on first load
- No urgency indicators (no "action required" callouts)

### Client Portal
- Funding progress bar visible but not emotionally compelling
- Credit score display is functional but not beautiful
- No celebration moments (no progress milestones)
- Documents section looks like a file manager

---

## Priority Improvements (Ranked by Trust Impact)

### Priority 1 — Hero Section Redesign (Homepage)
**Impact:** High | **Effort:** Medium | **Time:** 3–4 days

- Larger, bolder headline: "AI-Powered Business Funding" (32–40px mobile, 56px desktop)
- Subheadline focuses on outcome: "Get funded faster with your AI team working around the clock"
- Single prominent CTA: "Start Free Funding Assessment" (indigo pill button, 56px height)
- Trust badges directly below CTA: "256-bit encrypted | No credit pull | Results in minutes"
- Animated background: subtle floating particles or gradient pulse

### Priority 2 — Funding Progress Visualization (Client Portal)
**Impact:** High | **Effort:** Medium | **Time:** 2–3 days

- Full-width progress arc (not thin bar)
- Color: red → orange → yellow → green based on score
- Score displayed large in center (e.g., "73/100")
- 3 milestone markers: "Profile Created" → "Funding Ready" → "Approved"
- Animated fill on load (Framer Motion, 1.5s ease)
- Below arc: "Your top 3 actions to reach 90" — clickable action cards

### Priority 3 — Admin Dashboard Visual Hierarchy
**Impact:** High | **Effort:** Low | **Time:** 1–2 days

- Add red badge/pill to dock items that need attention (approvals, blockers)
- CEO Mode card as first visible element on dashboard load
- "Today's Focus" card with 3 prioritized action items
- Active worker count shown as glowing green dot in dock label
- Reduce initial data density — hide secondary stats in collapsed sections

### Priority 4 — Workforce Visualization Enhancement
**Impact:** Medium-High | **Effort:** Medium | **Time:** 3–4 days

- Make Virtual Office tab the default or prominently surfaced on AI Team page
- Add "pulse" animation to active employees (glowing ring for busy state)
- Room labels larger and bolder
- Today Panel: show actual task titles, not just counts
- Live provider status light in System Monitor room (green/red/orange)

### Priority 5 — Apple/Atlas Style Polish
**Impact:** Medium | **Effort:** Low-Medium | **Time:** 2–3 days

- Increase base font size to 15–16px (current feels small on desktop)
- Card border radius: 16–20px (more Apple-like)
- Shadows: softer, layered (box-shadow with 3 layers)
- Icon size: minimum 28px in dock, 40px in primary nav
- Spacing: add 4px more padding to cards and list items
- Micro-animations: hover scale 1.02, press scale 0.98 (100ms ease)

### Priority 6 — Client Trust Elements
**Impact:** Medium | **Effort:** Low | **Time:** 1 day

- Testimonial section below features (3 short quotes minimum)
- "As seen in" or partner logos strip (even placeholder)
- Security badge section: HTTPS, Supabase security, no PII sold
- FAQ section addressing common objections
- Money-back or satisfaction guarantee language (with legal review)

### Priority 7 — Mobile Dock Improvement
**Impact:** High on mobile | **Effort:** Low | **Time:** 1 day

- Bottom dock: max 6 items visible, rest hidden behind "More" button
- Larger tap targets (60px minimum height)
- Active item: filled background + larger emoji
- Scroll indicator if dock is wider than screen

---

## Quick Wins (Can Be Done This Week)

```bash
# 1. Fix mobile dock overflow
# Add maxItems={6} to AdminBottomDock, rest in overflow menu

# 2. Add red badge count to approvals dock item when pending > 0
# Read human_approval_requests?status=eq.pending&select=id

# 3. Increase CTA button height and font size on homepage

# 4. Add "DEMO MODE" banner removal from AdminTrading (already done)

# 5. Make CEO Mode card appear first on dashboard
```

---

## Design System Standards (Enforce Going Forward)

```css
/* Spacing */
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--space-lg: 24px;
--space-xl: 40px;

/* Border radius */
--radius-sm: 8px;
--radius-md: 16px;
--radius-lg: 24px;
--radius-pill: 999px;

/* Shadows */
--shadow-card: 0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04);
--shadow-elevated: 0 2px 8px rgba(0,0,0,0.12), 0 8px 24px rgba(0,0,0,0.10);

/* Typography */
--font-size-base: 15px;
--font-size-lg: 17px;
--font-size-display: 36px;
--font-size-hero: 52px;

/* Animation */
--transition-fast: 100ms ease;
--transition-normal: 200ms ease;
--transition-slow: 400ms ease;
```

---

## Subtasks in Supabase

| # | Title | Agent | Status |
|---|-------|-------|--------|
| 16 | Audit homepage, admin, and client portal for visual trust gaps | qa_worker | queued |
| 17 | Create UI polish task list: Apple/Atlas style, larger icons, reduced clutter | claude_code | queued |
| 18 | Prioritize dashboard and workforce visualization improvements | claude_code | queued |

---

## Implementation Order (When Ready to Build)

1. Mobile dock fix (1 hour)
2. Admin dashboard badge counts (2 hours)
3. Funding progress arc redesign (1 day)
4. Homepage hero redesign (2 days)
5. Workforce visualization pulse animations (1 day)
6. Apple polish pass: spacing, radius, shadows, font size (2 days)
7. Client trust section on homepage (1 day)

**Total estimated:** 8–10 development days  
**Recommended:** 2 per week alongside feature work
