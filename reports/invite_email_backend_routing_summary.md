# Invite Email Backend Routing — Summary
**Date:** 2026-05-12  
**Decision implemented:** Invite emails route through Nexus backend, not Netlify env secrets.

---

## What Changed

| Before | After |
|---|---|
| Frontend → Netlify `send-invite.js` → Resend API | Frontend → Netlify `admin-invite.js` (proxy) → Backend endpoint → Gmail SMTP |
| RESEND_API_KEY in Netlify | No email creds in Netlify |
| Invite status always "sent" (no real send) | Status is "sent" or "send_failed" based on actual delivery |
| Signup link = window.location.origin (wrong URL) | Signup link = NEXUS_APP_URL (canonical, server-side) |
| No delivery log | Supabase invited_users updated with result |

---

## Files Created / Modified

| File | Action |
|---|---|
| `control_center/control_center_server.py` | Added `POST /api/admin/tester-invites/send` endpoint |
| `nexuslive/netlify/functions/admin-invite.js` | Created thin proxy (no email creds) |
| `nexuslive/netlify/functions/send-invite.js` | **Removed** (previous Resend-direct function) |
| `nexuslive/src/components/admin/AdminInviteUsers.tsx` | Updated handleSend(), STATUS_META, UI |
| `.env` | Added NEXUS_APP_URL and TEST_MODE=false |

---

## Netlify Environment Variables Needed

Set these in Netlify → Site settings → Environment variables:

| Variable | Value | Notes |
|---|---|---|
| `NEXUS_API_URL` | `https://[your-backend-url]` | Already needed for nexus-api.js |
| `CONTROL_CENTER_ADMIN_TOKEN` | From nexus-ai `.env` | Backend admin auth |

No email credentials (RESEND_API_KEY, SMTP password) in Netlify.

---

## End-to-End Test Plan

1. Ensure backend is running and reachable at NEXUS_API_URL
2. Set NEXUS_APP_URL + TEST_MODE=false in nexus-ai .env → restart backend
3. Set NEXUS_API_URL + CONTROL_CENTER_ADMIN_TOKEN in Netlify → redeploy nexuslive
4. Open admin portal → Invite Users → Add invite for goclearonline@gmail.com
5. Click "Send Welcome Email"
6. Verify: email received at Gmail
7. Verify: email subject = "You've Been Invited to Join Nexus Beta"
8. Verify: signup link = `https://nexus.goclearonline.com/?invited=true&email=...`
9. Verify: invited_users.invite_status = "sent" in Supabase
10. Verify: no billing triggered (subscription_status = "waived")
11. Click signup link → verify it opens the correct app URL
12. Complete signup → verify dashboard access

---

## Safety Preserved

- No secrets exposed to frontend or browser
- No auto client messaging (operator-initiated only, requires admin login)
- Waived billing preserved: `subscription_status: 'waived'` set at invite creation, untouched by send
- Email is operational only — no autonomous sends
- All safety flags unchanged

---

## Hermes Visibility

To check invite delivery status from Hermes, add keyword routing for `"invite status"` → query Supabase `invited_users` sorted by `created_at` desc. Currently requires direct Supabase query or control center admin UI.

Future: `/invite status` Telegram command could return last 5 invites with delivery status.
