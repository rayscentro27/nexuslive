# Nexus Visual Trust — Execution Plan

**Created:** 2026-05-19  
**Status:** ACTIVE — qa_worker + claude_code subtasks queued  
**Goal:** Premium, alive, trustworthy UI before client launch

---

## VISUAL TRUST AUDIT FINDINGS

### Homepage (nexuslive)

| Issue | Severity | Impact |
|-------|----------|--------|
| Hero headline too small / generic | High | First impression fails |
| CTA button not dominant | High | Low conversion |
| No trust signals above fold | High | Users bounce |
| Features section too text-heavy | Medium | Cognitive load |
| No "live" indicators | Medium | Feels static |
| Footer too sparse | Low | Missed credibility |

### Admin Dashboard

| Issue | Severity | Impact |
|-------|----------|--------|
| Bottom dock overflows on mobile | High | Unusable on mobile |
| No visual priority hierarchy | High | Everything looks equal |
| No "action required" callouts | High | Ray misses important items |
| Workforce visualization buried | Medium | Main feature not prominent |
| Too many visible items at once | Medium | Overwhelming |

### Client Portal

| Issue | Severity | Impact |
|-------|----------|--------|
| Funding progress bar thin + generic | High | Low emotional impact |
| No celebration/milestone moments | Medium | No motivation |
| Documents section looks like file manager | Medium | Not premium |
| Credit score display basic | Medium | Should feel like a score reveal |

---

## QUICK VISUAL WINS (< 4 Hours Each)

### Win 1 — Mobile Dock Fix
**File:** `src/components/admin/AdminPortal.tsx`  
**Change:** Show max 6 dock items, collapse rest behind "More" button  
**Impact:** Mobile becomes usable immediately  

```tsx
// Current: all items always visible (causes scroll)
// Fix: Show first 6, add overflow menu

const DOCK_PRIMARY = ADMIN_DOCK.slice(0, 6);
const DOCK_OVERFLOW = ADMIN_DOCK.slice(6);

// Add overflow toggle button as last dock item
```

### Win 2 — Red Badge on Pending Approvals
**File:** `src/components/admin/AdminPortal.tsx` (dock button)  
**Change:** When human_approval_requests.status = pending > 0, show red dot on ⚡ Command dock item  
**Impact:** Ray instantly sees when action is needed  

### Win 3 — CTA Button Size Increase (Homepage)
**Change:** Increase CTA button from current height to 56px, font 18px, border-radius 28px  
**Impact:** Conversion rate improvement  

### Win 4 — Typography Upgrade
**Change:** Increase base body font from ~14px to 15–16px across admin and client portal  
**Impact:** Immediately more premium feel, less strain  

### Win 5 — Card Shadow Depth
**Change:** Upgrade card shadows from flat to layered (3-layer box-shadow)  
**Before:** `box-shadow: 0 1px 3px rgba(0,0,0,0.1)`  
**After:**
```css
box-shadow: 
  0 1px 2px rgba(0,0,0,0.07),
  0 4px 12px rgba(0,0,0,0.06),
  0 8px 24px rgba(0,0,0,0.04);
```

---

## HIGH TRUST UPGRADES (1–2 Days Each)

### Upgrade 1 — Funding Progress Arc (Client Portal)

**Replace:** Thin progress bar  
**With:** Full circular arc with large centered score number

```tsx
// SVG arc implementation
const circumference = 2 * Math.PI * 90; // radius 90
const progress = (score / 100) * circumference * 0.75; // 270-degree arc

<svg width="240" height="180" viewBox="0 0 240 200">
  {/* Track */}
  <path d="M30,150 A90,90 0 1,1 210,150" fill="none" stroke="#e5e7eb" strokeWidth="16" strokeLinecap="round"/>
  {/* Progress - color: red→orange→yellow→green based on score */}
  <path d="M30,150 A90,90 0 1,1 210,150" fill="none" 
    stroke={scoreColor(score)} strokeWidth="16" strokeLinecap="round"
    strokeDasharray={`${progress} ${circumference}`}/>
  {/* Score number */}
  <text x="120" y="135" textAnchor="middle" fontSize="48" fontWeight="bold">{score}</text>
  <text x="120" y="160" textAnchor="middle" fontSize="14" fill="#6b7280">/ 100</text>
</svg>
```

**Color scale:**
- 0–40: #ef4444 (red)
- 41–60: #f97316 (orange)
- 61–75: #eab308 (yellow)
- 76–90: #22c55e (green)
- 91–100: #10b981 (emerald)

### Upgrade 2 — "Today's Focus" Dashboard Card

**Add:** First card on Admin Dashboard — shows 3 prioritized actions  
**Data source:** `human_approval_requests` + `ai_task_queue` + roadmap  

```tsx
<TodayFocusCard items={[
  { type: 'approval', urgency: 'high', label: 'Review trading research gate' },
  { type: 'task', urgency: 'medium', label: 'Publish funding audit landing page' },
  { type: 'metric', urgency: 'low', label: 'Check provider health — 4 offline' },
]} />
```

### Upgrade 3 — Live Worker Pulse Animations

**File:** `src/components/admin/NexusVirtualOffice.tsx`  
**Add:** Glowing ring animation on active employees  

```tsx
// Working state — animated pulse ring
const WorkingPulse = () => (
  <motion.div
    style={{ position: 'absolute', inset: -4, borderRadius: '50%', border: '2px solid currentColor' }}
    animate={{ opacity: [0.6, 0, 0.6], scale: [1, 1.4, 1] }}
    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
  />
);
```

### Upgrade 4 — Homepage Hero Redesign

**Current weaknesses:** Small headline, weak CTA, no trust signals  
**Target state:**

```tsx
<HeroSection>
  {/* Badge */}
  <TrustBadge>AI-Powered • No Credit Pull • Results in Minutes</TrustBadge>
  
  {/* Headline — 52px desktop, 36px mobile */}
  <H1>Your Business Deserves Funding.</H1>
  <H1Accent>Let's Make Sure You're Ready.</H1Accent>
  
  {/* Subheadline */}
  <Subhead>Get your personalized Funding Readiness Score and a clear action plan — 
  built by AI, reviewed by humans.</Subhead>
  
  {/* CTA */}
  <PrimaryCTA size="lg" width="280px" height="56px">
    Start Free Assessment →
  </PrimaryCTA>
  <SecondaryText>No credit pull · Free to start · Results same day</SecondaryText>
  
  {/* Social proof strip */}
  <SocialProof>
    <Metric>127 businesses assessed this month</Metric>
    <Metric>Average score improvement: +23 points</Metric>
    <Metric>4.9★ satisfaction</Metric>
  </SocialProof>
</HeroSection>
```

---

## CLIENT CONFIDENCE IMPROVEMENTS

### Trust Elements to Add to Homepage

1. **Security badge row** (below CTA):
   - 🔒 256-bit encrypted
   - 🚫 No credit pull
   - 🔐 No PII sold
   - ✅ HTTPS secured

2. **Testimonial section** (3 short quotes):
   - Format: Quote → Name → Business type → Location
   - Start with: "As Seen By" or "Trusted By" placeholder while building reviews

3. **How It Works section** (3-step process):
   - Step 1: Answer 12 questions about your business (5 min)
   - Step 2: AI analyzes your profile against lender criteria
   - Step 3: Get your score + personalized action plan

4. **FAQ section** (5 questions, expandable):
   - Will this affect my credit? No.
   - How long does it take? 5 min to complete, same-day results.
   - Is this financial advice? No — educational analysis only.
   - What if my score is low? That's the point — low score = clear roadmap.
   - Can I use this for multiple businesses? Yes.

---

## DESIGN SYSTEM TOKENS (Apply Immediately)

```ts
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
  },
  fontSize: {
    xs: '12px', sm: '13px', base: '15px',
    md: '17px', lg: '20px', xl: '24px',
    '2xl': '32px', '3xl': '40px', hero: '52px',
  },
  animation: {
    fast: '100ms ease', normal: '200ms ease',
    slow: '400ms ease', spring: 'spring(1, 80, 10, 0)',
  },
} as const;
```

---

## PRIORITIZED IMPLEMENTATION ROADMAP

| Priority | Task | Time | Files |
|----------|------|------|-------|
| P1 | Mobile dock overflow fix | 1h | AdminPortal.tsx |
| P1 | Red badge on approval count | 2h | AdminPortal.tsx |
| P1 | Typography + spacing increase | 2h | global CSS |
| P2 | Funding progress arc | 4h | AdminFunding.tsx |
| P2 | Card shadow depth upgrade | 1h | component CSS |
| P2 | Homepage CTA button size | 1h | homepage components |
| P3 | Today's Focus card on dashboard | 4h | AdminDashboard.tsx |
| P3 | Worker pulse animations | 3h | NexusVirtualOffice.tsx |
| P3 | Homepage hero redesign | 1 day | Homepage.tsx |
| P4 | Social proof + testimonials | 4h | Homepage.tsx |
| P4 | How It Works section | 2h | Homepage.tsx |
| P4 | FAQ accordion | 2h | Homepage.tsx |
| P5 | Client portal milestone moments | 3h | client portal |

**Week 1 focus (P1 items):** ~6 hours total. Immediate impact, low risk.  
**Week 2 focus (P2 items):** ~10 hours total. High emotional impact.  
**Week 3+ (P3–P5):** Full premium UI conversion.
