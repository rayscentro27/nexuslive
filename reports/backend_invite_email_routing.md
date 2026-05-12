# Backend Invite Email Routing
**Date:** 2026-05-12  
**Decision:** Route invite emails through Nexus backend (not Netlify env secrets)

---

## Architecture

```
Admin UI (nexuslive)
    ↓ POST with Supabase JWT
/.netlify/functions/admin-invite   [thin proxy — adds X-Admin-Token server-side]
    ↓ POST with X-Admin-Token
Nexus backend: POST /api/admin/tester-invites/send
    ↓
_send_tester_email_live()   [Gmail SMTP via NEXUS_EMAIL + NEXUS_EMAIL_PASSWORD]
    ↓
Email delivered to invitee
    ↓
Backend updates Supabase: invited_users.invite_status, invite_sent_at, signup_link
    ↓
Frontend re-fetches invite list — status visible in admin dashboard
```

---

## Backend Endpoint

**Route:** `POST /api/admin/tester-invites/send`  
**File:** `control_center/control_center_server.py`  
**Auth:** `X-Admin-Token` header (= `CONTROL_CENTER_ADMIN_TOKEN` env var)

### Request body
```json
{
  "invite_id": "supabase-row-uuid",   // required for precise DB update
  "email": "user@example.com",        // required
  "name": "User Name",                // used in email greeting
  "membership_level": "admin_test",   // default if not provided
  "invited_by": "admin-user-id",      // audit log
  "note": ""                          // optional admin note in email
}
```

### Response
```json
{
  "ok": true,
  "invite_id": "uuid",
  "email": "user@example.com",
  "delivery_status": "sent",          // sent | send_failed | preview_only
  "sent_at": "2026-05-12T...",
  "signup_link": "https://nexus.goclearonline.com/?invited=true&email=...",
  "provider": "smtp_gmail",
  "invited_by": "admin",
  "waived_subscription": true,
  "error": null,
  "test_mode": false
}
```

### Delivery states
| Status | Meaning |
|---|---|
| `sent` | Email delivered via Gmail SMTP |
| `send_failed` | SMTP error — error field contains reason |
| `preview_only` | TEST_MODE=true — email not sent, body returned for preview |

---

## Netlify Proxy Function

**File:** `nexuslive/netlify/functions/admin-invite.js`  
**What it does:**
- Validates Supabase JWT from admin user (must be present)
- Adds `X-Admin-Token` header server-side (never exposed to browser)
- Forwards POST to backend `NEXUS_API_URL/api/admin/tester-invites/send`
- No email credentials stored in Netlify

**Env vars required on Netlify:**
| Variable | Description |
|---|---|
| `NEXUS_API_URL` | Public URL of Nexus control center backend |
| `CONTROL_CENTER_ADMIN_TOKEN` | Backend admin auth token |

---

## Email Template

Template: `build_tester_email()` in `scripts/prelaunch_utils.py`  
Content: Beta invite, platform description, mobile install instructions, waived subscription note, compliance disclaimer  
Signup link: `NEXUS_APP_URL/?invited=true&email=<encoded>` — uses server-side canonical URL

---

## Backend Env Vars Added

```
NEXUS_APP_URL=https://nexus.goclearonline.com   # canonical invite link URL
TEST_MODE=false                                  # enables live email sending
```

`TEST_MODE=false` is required. If `TEST_MODE=true` (default), the endpoint returns `preview_only` and no email is sent. This matches the existing `send-tester-email` endpoint behavior.

---

## Database Updates

Backend updates `invited_users` table on each send attempt:
- `invite_status`: `sent` or `send_failed`
- `invite_sent_at`: timestamp on success, null on failure
- `signup_link`: canonical URL (overrides any window.location.origin value from frontend)

---

## Frontend Changes

**File:** `nexuslive/src/components/admin/AdminInviteUsers.tsx`

Changes:
- `SendWelcomeModal.handleSend()` — now calls `/.netlify/functions/admin-invite` with Supabase JWT
- Removed WELCOME_BODY template (backend generates the email content)
- Added `sendError` state — shows error message in UI on delivery failure
- `STATUS_META` — added `send_failed` status with red styling
- Delivery info box updated to reflect new backend routing

**Removed:** `nexuslive/netlify/functions/send-invite.js` (previous Netlify-direct Resend function)

---

## Why This Is Better Than Netlify-Direct

| Concern | Netlify-Direct (Old) | Backend-Routed (New) |
|---|---|---|
| Email credentials in Netlify | RESEND_API_KEY required | Not needed |
| Email provider | Resend | Gmail SMTP (existing) |
| Delivery logging | None | Supabase invited_users update |
| Hermes visibility | None | Backend logs + Supabase |
| Centralized email system | No | Yes — same as CEO reports |
| Invite link URL | window.location.origin (wrong) | Server-side canonical URL |
| Auth to backend | N/A | X-Admin-Token (server-side) |

---

## Audit Trail

Every send attempt logs to:
- Python logger: `email=... status=... invite_id=... invited_by=...`
- Supabase `invited_users`: `invite_status`, `invite_sent_at`, `signup_link`
- Response JSON: delivery_status, sent_at, error if any

Hermes can inspect: `supabase.from('invited_users').select('*')` or query via admin API.
