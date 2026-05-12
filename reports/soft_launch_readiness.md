# Soft Launch Readiness Report
**Date:** 2026-05-12  
**Phase:** E — Soft Launch + Testers

---

## E1 — Invite Flow Status

### What's Working
- `invited_users` Supabase table: id, name, email, invite_status, subscription_status (waived), auth_user_id
- Backend endpoint: `POST /api/admin/tester-invites/send` → Gmail SMTP
- Netlify thin proxy: `admin-invite.js` → validates Supabase JWT → adds X-Admin-Token → backend
- Admin UI: `AdminInviteUsers.tsx` → shows invite status, send modal, delivery error state
- Invite link: `https://nexus.goclearonline.com/?invited=true&email=<encoded>` (canonical URL from `NEXUS_APP_URL`)
- Waived billing: `subscription_status=waived` preserved through send flow

### Remaining Operator Actions
1. Set Netlify env vars:
   - `NEXUS_API_URL` = backend public URL
   - `CONTROL_CENTER_ADMIN_TOKEN` = value from nexus-ai `.env`
2. Redeploy nexuslive on Netlify

### Test Plan (After Netlify Setup)
1. Admin portal → Invite Users → Add invite → Send Welcome
2. Confirm email received at `goclearonline@gmail.com`
3. Confirm signup link = `https://nexus.goclearonline.com/?invited=true&email=...`
4. Confirm `invite_status = 'sent'` in Supabase
5. Confirm `subscription_status = 'waived'` unchanged

---

## E2 — Tester Feedback System

### Recommended Approach (Not Yet Implemented)
A lightweight feedback table in Supabase:

```sql
CREATE TABLE tester_feedback (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES auth.users(id),
    feedback_type TEXT NOT NULL,  -- 'bug' | 'ux' | 'hermes' | 'feature' | 'onboarding'
    message      TEXT NOT NULL,
    page         TEXT,            -- which page/component
    severity     TEXT,            -- 'critical' | 'medium' | 'low'
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    reviewed      BOOLEAN DEFAULT false
);
```

Hermes command: `/feedback` in Telegram to review unread tester feedback

### Current Alternative
Use the existing `Messages` tab in the app for tester communication.

---

## E3 — Marketing Infrastructure Status

### Complete
- `marketing/` directory: 11+ documents (ICP, content calendar, landing copy, email sequences)
- Landing page: `Landing.tsx` — SEO meta, CTA, mobile-responsive
- Onboarding: AuthProvider + Dashboard first-run flow
- App install: `InstallPrompt.tsx` — PWA install on mobile

### Gaps
- Social profiles: accounts created, not yet filled (see `marketing/social_profile_copy.md`)
- Email automation: single invite email only, no drip sequence wired yet
- Analytics: no onboarding funnel tracking yet

---

## E4 — Controlled Beta Preparation

### Phase Criteria (5-10 Testers)
- [ ] Netlify env vars set + nexuslive redeployed
- [ ] Invite email delivery confirmed (test with goclearonline@gmail.com)
- [ ] Admin can monitor: Supabase `invited_users` table
- [ ] Dashboard loads for invited user (waived billing)
- [ ] Hermes reachable via FloatingChat component
- [ ] Mobile PWA installable on iPhone

### Monitoring During Beta
- Supabase: `invited_users.auth_user_id` populated when tester signs up
- Dashboard: Admin portal → Invite Users → see invite_status per tester
- Hermes: can report on new signups via `invited_users` query
- No automated scaling until first 5 testers have been reviewed

---

## Overall Launch Blockers (Ordered by Priority)

| Blocker | Owner | Notes |
|---|---|---|
| Netlify env vars not set | Operator | NEXUS_API_URL + CONTROL_CENTER_ADMIN_TOKEN |
| Invite email delivery unverified | Operator | Test after Netlify redeploy |
| `LIVE_TRADING=false` confirmed | ✅ Fixed | Done this pass |
| `NEXUS_DRY_RUN=true` confirmed | ✅ Fixed | Done this pass |
| Mobile bottom nav | ✅ Built | MobileBottomNav.tsx |
| Circuit breaker system | ✅ Built | lib/circuit_breaker.py |
