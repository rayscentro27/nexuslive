# Nexus Visual Trust — ACTIVE

**Status:** ACTIVE — Prioritized execution roadmap  
**Last Updated:** 2026-05-19  
**Goal:** Premium, alive, trustworthy UI before next client wave

---

## VISUAL AUDIT — FINDINGS BY AREA

### Homepage (nexuslive)

| Issue | Severity | Impact | Fix Time |
|-------|----------|--------|----------|
| Hero headline too small + generic | Critical | First impression fails | 2h |
| CTA button not dominant | Critical | Low conversion | 30min |
| No trust signals above fold | High | Users bounce | 1h |
| Features section too text-heavy | High | Cognitive overload | 2h |
| No "alive" indicators | Medium | Feels static | 3h |
| Footer too sparse | Low | Missed credibility | 1h |

### Admin Dashboard

| Issue | Severity | Impact | Fix Time |
|-------|----------|--------|----------|
| Bottom dock overflows on mobile | Critical | Unusable on mobile | 2h |
| No visual priority hierarchy | High | Everything looks equal | 3h |
| No "action required" callouts | High | Ray misses urgency | 2h |
| Workforce visualization (done) | Resolved | ✅ Simulation live | — |
| Too many visible items at once | Medium | Overwhelming | 2h |

### Client Portal

| Issue | Severity | Impact | Fix Time |
|-------|----------|--------|----------|
| Funding progress bar thin + generic | High | Low emotional impact | 4h |
| No celebration/milestone moments | Medium | No motivation | 3h |
| Documents section looks like file manager | Medium | Not premium | 2h |
| Credit score display basic | Medium | Should feel like a reveal | 3h |

---

## PRIORITIZED IMPLEMENTATION ROADMAP

| Priority | Task | Time | File | Status |
|----------|------|------|------|--------|
| P0 | Workforce Virtual Office (simulation) | Done | NexusVirtualOffice.tsx | ✅ LIVE |
| P1 | Mobile dock overflow fix | 1h | AdminPortal.tsx | 🟡 Queued |
| P1 | Red badge on pending approvals | 1h | AdminPortal.tsx | 🟡 Queued |
| P1 | CTA button size increase (56px) | 30min | Homepage | 🟡 Pending |
| P1 | Typography upgrade (15–16px base) | 2h | global CSS | 🟡 Pending |
| P2 | Card shadow depth upgrade | 1h | components | 🟡 Pending |
| P2 | Funding progress arc (SVG circle) | 4h | AdminFunding.tsx | 🟡 Planned |
| P2 | Homepage hero redesign | 4h | Homepage | 🟡 Planned |
| P3 | "Today's Focus" card on dashboard | 4h | AdminDashboard.tsx | 🔵 Month 2 |
| P3 | Worker pulse animations (Sage flow done) | Done | NexusVirtualOffice.tsx | ✅ LIVE |
| P3 | Social proof + testimonials | 4h | Homepage | 🔵 Month 2 |
| P4 | How It Works section | 2h | Homepage | 🔵 Month 2 |
| P4 | FAQ accordion | 2h | Homepage | 🔵 Month 2 |
| P5 | Client portal milestone moments | 3h | Client portal | 🔵 Month 3 |

---

## QUICK VISUAL WINS (< 2 Hours Each)

### Win 1 — Mobile Dock Overflow Fix

**File:** `src/components/admin/AdminPortal.tsx`  
**Change:** Show max 6 dock items, collapse rest behind "More" button

```tsx
// Current: all items always visible (causes overflow on mobile)
// Fix: Show first 6, add "More" overflow menu for rest

const DOCK_PRIMARY = ADMIN_DOCK.slice(0, 6);
const DOCK_OVERFLOW = ADMIN_DOCK.slice(6);

// In dock render:
{DOCK_PRIMARY.map(item => <DockButton key={item.id} {...item} />)}
{DOCK_OVERFLOW.length > 0 && (
  <DockButton
    id="more"
    emoji="⋯"
    label="More"
    onClick={() => setShowOverflow(v => !v)}
    badge={DOCK_OVERFLOW.length}
  />
)}
{showOverflow && (
  <div className="dock-overflow-menu">
    {DOCK_OVERFLOW.map(item => <DockButton key={item.id} {...item} />)}
  </div>
)}
```

---

### Win 2 — Red Badge on Pending Approvals

**File:** `src/components/admin/AdminPortal.tsx`  
**Change:** When `human_approval_requests.status = pending > 0`, show red dot on ⚡ Command dock item

```tsx
// In dock button for 'workforce-command':
<DockButton
  id="workforce-command"
  emoji="⚡"
  label="Command"
  active={activeTab === 'workforce-command'}
  badge={pendingApprovals > 0 ? pendingApprovals : undefined}
  badgeColor="#ef4444"
  onClick={() => setActiveTab('workforce-command')}
/>

// Fetch pending approvals (already live in NexusWorkforceCommand)
// Pass count down to AdminPortal dock
```

---

### Win 3 — CTA Button Size Increase

**File:** Homepage component  
**Change:** Increase CTA from ~40px to 56px height, 18px font, 28px border-radius

```tsx
// Before:
<button className="primary-cta">Start Free Assessment</button>

// After:
<button style={{
  height: 56,
  padding: '0 32px',
  fontSize: 18,
  fontWeight: 700,
  borderRadius: 28,
  background: 'linear-gradient(135deg, #3d5af1, #6366f1)',
  color: '#fff',
  border: 'none',
  cursor: 'pointer',
  boxShadow: '0 4px 24px rgba(61,90,241,0.35)',
  letterSpacing: '-0.01em',
}}>
  Start Free Assessment →
</button>
```

---

### Win 4 — Typography Upgrade

**File:** `src/index.css` or global styles  
**Change:** Increase base body font from 14px to 15–16px

```css
/* Before */
body { font-size: 14px; }

/* After */
body {
  font-size: 15px;          /* Base reading size */
  line-height: 1.6;         /* Better readability */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Scale up card body text */
.card-body { font-size: 14px; }
.card-description { font-size: 13px; }
.metric-value { font-size: 28px; font-weight: 800; }
.metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }
```

---

### Win 5 — Card Shadow Depth

**File:** Component CSS or inline styles  
**Before:** `box-shadow: 0 1px 3px rgba(0,0,0,0.1)`  
**After:**

```css
.card {
  box-shadow:
    0 1px 2px rgba(0,0,0,0.07),
    0 4px 12px rgba(0,0,0,0.06),
    0 8px 24px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease;
}

.card:hover {
  box-shadow:
    0 2px 4px rgba(0,0,0,0.08),
    0 8px 24px rgba(0,0,0,0.08),
    0 16px 48px rgba(0,0,0,0.06);
}

.card-elevated {
  box-shadow:
    0 2px 8px rgba(0,0,0,0.12),
    0 8px 24px rgba(0,0,0,0.10),
    0 16px 48px rgba(0,0,0,0.08);
}
```

---

## HIGH TRUST UPGRADES (4+ Hours Each)

### Upgrade 1 — Funding Progress Arc (Client Portal)

**Replace:** Thin progress bar  
**With:** Full SVG circular arc with large centered score number

```tsx
function FundingScoreArc({ score }: { score: number }) {
  const r = 90;
  const circumference = 2 * Math.PI * r;
  const arcFraction = 0.75; // 270-degree arc
  const progress = (score / 100) * circumference * arcFraction;

  const color = score < 40 ? '#ef4444'
    : score < 61 ? '#f97316'
    : score < 76 ? '#eab308'
    : score < 91 ? '#22c55e'
    : '#10b981';

  return (
    <svg width="240" height="200" viewBox="0 0 240 200">
      {/* Track (grey background arc) */}
      <path
        d="M30,165 A90,90 0 1,1 210,165"
        fill="none" stroke="#e5e7eb" strokeWidth="16" strokeLinecap="round"
      />
      {/* Progress arc */}
      <path
        d="M30,165 A90,90 0 1,1 210,165"
        fill="none" stroke={color} strokeWidth="16" strokeLinecap="round"
        strokeDasharray={`${progress} ${circumference}`}
        style={{ transition: 'stroke-dasharray 1s ease' }}
      />
      {/* Score number */}
      <text x="120" y="148" textAnchor="middle"
        fontSize="52" fontWeight="800" fill={color}>
        {score}
      </text>
      <text x="120" y="172" textAnchor="middle"
        fontSize="14" fill="#6b7280">
        / 100
      </text>
      <text x="120" y="190" textAnchor="middle"
        fontSize="11" fontWeight="600" fill={color}>
        {score >= 80 ? 'STRONG' : score >= 60 ? 'GOOD' : score >= 40 ? 'FAIR' : 'NEEDS WORK'}
      </text>
    </svg>
  );
}
```

**Color scale:**
- 0–40: `#ef4444` (red — not ready)
- 41–60: `#f97316` (orange — conditional)
- 61–75: `#eab308` (yellow — approaching ready)
- 76–90: `#22c55e` (green — ready)
- 91–100: `#10b981` (emerald — strong)

---

### Upgrade 2 — Homepage Hero Redesign

**Target state:**

```tsx
<HeroSection>
  {/* Trust badge above headline */}
  <TrustBadge>
    AI-Powered · No Credit Pull · Results in Minutes
  </TrustBadge>

  {/* Main headline — 52px desktop, 36px mobile */}
  <H1>Your Business Deserves Funding.</H1>
  <H1Accent>Let's Make Sure You're Ready.</H1Accent>

  {/* Subheadline */}
  <Subhead>
    Get your personalized Funding Readiness Score and a clear action plan
    — built by AI, reviewed by humans.
  </Subhead>

  {/* Primary CTA */}
  <PrimaryCTA>Start Free Assessment →</PrimaryCTA>
  <SecondaryText>No credit pull · Free to start · Results same day</SecondaryText>

  {/* Social proof strip */}
  <SocialProofRow>
    <Metric>127 businesses assessed this month</Metric>
    <Metric>Average score improvement: +23 points</Metric>
    <Metric>4.9★ satisfaction</Metric>
  </SocialProofRow>
</HeroSection>
```

**Mobile:** Stack vertically, 36px headline, full-width CTA button

---

### Upgrade 3 — "Today's Focus" Dashboard Card

**Add:** First card on Admin Dashboard — 3 prioritized actions

```tsx
<TodayFocusCard items={[
  { type: 'approval', urgency: 'high', label: 'Review pending approval — 1 item' },
  { type: 'content', urgency: 'medium', label: 'PAYDEX article scheduled to publish' },
  { type: 'metric', urgency: 'low', label: 'Provider health — 4/7 online' },
]} />
```

**Data sources:**
- `human_approval_requests` (pending count)
- `agent_dispatch_tasks` (next item in queue)
- `provider_health` (online count)

---

## DESIGN SYSTEM TOKENS

```typescript
// tokens.ts — add to nexuslive design system
export const tokens = {
  spacing: {
    xs: '4px', sm: '8px', md: '16px',
    lg: '24px', xl: '40px', '2xl': '64px',
  },
  radius: {
    sm: '8px', md: '16px', lg: '24px',
    xl: '32px', pill: '9999px',
  },
  shadow: {
    card: '0 1px 2px rgba(0,0,0,0.07), 0 4px 12px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04)',
    elevated: '0 2px 8px rgba(0,0,0,0.12), 0 8px 24px rgba(0,0,0,0.10), 0 16px 48px rgba(0,0,0,0.08)',
    floating: '0 4px 16px rgba(0,0,0,0.16), 0 16px 48px rgba(0,0,0,0.14)',
    cta: '0 4px 24px rgba(61,90,241,0.35)',
  },
  fontSize: {
    xs: '11px', sm: '12px', base: '15px',
    md: '17px', lg: '20px', xl: '24px',
    '2xl': '32px', '3xl': '40px', hero: '52px',
  },
  color: {
    primary: '#3d5af1',
    accent: '#6366f1',
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    text: {
      primary: '#1e293b',
      secondary: '#475569',
      muted: '#94a3b8',
      inverse: '#ffffff',
    },
    surface: {
      base: '#ffffff',
      raised: '#f8fafc',
      overlay: '#f1f5f9',
    },
  },
  animation: {
    fast: '100ms ease',
    normal: '200ms ease',
    slow: '400ms ease',
  },
} as const;
```

---

## CLIENT CONFIDENCE IMPROVEMENTS

### Homepage — Trust Elements to Add

1. **Security badge row** (below CTA):
   - 🔒 256-bit encrypted
   - 🚫 No credit pull
   - 🔐 No PII sold
   - ✅ HTTPS secured
   - 🏦 Trusted by 100+ businesses

2. **How It Works section** (3 steps):
   - Step 1: Answer 12 questions about your business (5 min)
   - Step 2: AI analyzes your profile against lender criteria
   - Step 3: Get your score + personalized action plan (same day)

3. **Social proof strip** (start with estimates, update with real data):
   - "127 businesses assessed this month"
   - "Average score improvement: +23 points in 60 days"
   - "4.9★ client satisfaction"

4. **FAQ accordion** (5 questions, expandable):
   - Will this affect my credit? No.
   - How long does it take? 5 min to complete, same-day results.
   - Is this financial advice? No — educational analysis only.
   - What if my score is low? A low score = a clear roadmap.
   - Can I use this for multiple businesses? Yes.

5. **Compliance footer:**
   - "Educational analysis only. Not a lender or financial advisor. Results based on self-reported information."

---

## VISUAL KPIs TO TRACK

| Metric | Baseline | Target (30 days) |
|--------|----------|-----------------|
| Homepage bounce rate | [measure] | < 60% |
| CTA click-through rate | [measure] | > 8% |
| Mobile usability score | [measure] | > 85 |
| Page load time | [measure] | < 2.5s |
| Audit conversion rate | [measure] | > 3% |
