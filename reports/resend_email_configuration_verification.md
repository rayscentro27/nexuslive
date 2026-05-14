# Resend Email Configuration Verification
Date: 2026-05-13

## Config Status

| Check | Status | Notes |
|-------|--------|-------|
| RESEND_API_KEY in nexus-ai .env | ✅ Present | Key prefix: re_VPM2jPSo_ |
| RESEND_API_KEY in nexuslive .env | ✅ Present | Same key |
| Domain goclearonline.cc configured | Unknown | Can't verify while API blocked |
| API call test | ❌ HTTP 403 (Cloudflare error 1010) | IP block — not a key/code issue |
| SMTP Gmail fallback | ⚠️ Requires SCHEDULER_EMAIL_ENABLED=true | Fallback available |

## Error Diagnosis

```
HTTP Error 403: error code 1010
```

Cloudflare error 1010 = "The owner of this website (Resend) has banned the IP address of the request." This is a **network-level block** on the Mac Mini's IP, not an invalid API key.

Resolution options:
1. Wait for Cloudflare block to lift (auto-expires in 24-48h typically)
2. Access Resend dashboard from a different network/IP to verify domain status
3. Use VPN to make API calls until block clears

## Code Upgrades Applied

### notifications/operator_notifications.py (UPGRADED)
- Added `_send_via_resend()` — Resend API with HTML email support
- Added `_send_via_smtp()` — Gmail SMTP with HTML multipart support
- Updated `send_operator_email(subject, body, html_body=None)` — tries Resend first, falls back to SMTP
- Both paths support HTML via `html_body` parameter

### ceo_worker.py (UPGRADED)
- Added `_build_html_brief(briefing)` — premium dark-header HTML email
- `_send_email()` now passes `html_body=_build_html_brief(briefing)` to operator_notifications
- Plain text fallback preserved for SMTP path

## CEO Email HTML Template

Features:
- Dark gradient header (linear-gradient #1a1c3a → #3d5af1)
- Grouped sections: Blockers / Updates / Recommended Actions / Safety Status
- Color-coded section headers (red for blockers, blue for updates, purple for actions, green for safety)
- Clean footer with Telegram reference
- Max-width 600px, responsive

## Email Flow

```
1. _send_email(briefing) called from ceo_worker
2. → _build_html_brief(briefing) generates HTML
3. → send_operator_email(subject, body, html_body) called
4.   → Try Resend API (HTML) — if 403, log and continue
5.   → Fall back to Gmail SMTP (HTML multipart)
6.   → Returns (True/False, detail_string)
```

## Env Vars Required for Email

```
# Resend (primary - HTML capable)
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=Nexus <onboarding@goclearonline.cc>
SCHEDULER_EMAIL_TO=goclearonline@gmail.com

# SMTP Gmail (fallback)
SCHEDULER_EMAIL_ENABLED=true
NEXUS_EMAIL=your@gmail.com
NEXUS_EMAIL_PASSWORD=app_password
SCHEDULER_EMAIL_TO=goclearonline@gmail.com
```

## Tester Invite Email Path

The tester invite email uses a different path (Admin UI → invite form) which calls a Supabase function directly. That path is operational. The Resend/SMTP upgrade only affects the automated CEO operational briefings.
