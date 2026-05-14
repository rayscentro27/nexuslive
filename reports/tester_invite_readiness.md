# Tester Invite Readiness
Date: 2026-05-13

## Invite Flow Status

| Component | Status | Notes |
|-----------|--------|-------|
| Production URL | ✅ Live | https://goclearonline.cc/ |
| invited_users table | ✅ 1 record | rayscentro@yahoo.com — invite_status: pending |
| prelaunch_testers table | ✅ 1 record | tester_access: true, welcome_email_not_sent |
| Invite link | ✅ Generated | https://goclearonline.cc/?invited=true&email=rayscentro%40yahoo.com |
| Mobile install instructions | ✅ Written | iPhone/Android steps in tester_invite_email_final.md |
| Invite email template | ✅ Finalized | marketing/tester_invite_email_final.md |

## What Remains Before Sending

1. **Send the invite email** — copy from `marketing/tester_invite_email_final.md`, send to rayscentro@yahoo.com
2. **Update invite_sent_at** in `invited_users` table once email sent
3. **Verify login flow** — confirm rayscentro@yahoo.com can create account via invite link

## Invite Email Key Points

- Subject: "You're in — Nexus Beta is ready for you"
- Link: https://goclearonline.cc/?invited=true&email=rayscentro%40yahoo.com
- Mobile install: iPhone (Safari → Share → Add to Home Screen) + Android (Chrome → Add to Home Screen)
- Support: reply to email or Telegram
- Access: free_full_access, subscription waived, 138-day grace period

## Demo Experience for Tester

On first load, tester will see:
1. Onboarding → business details + credit goal + funding target
2. Dashboard with credit hero card (animates green if credit uploaded)
3. NexusIntelligencePanel — shows what Nexus has researched
4. Quick Stats strip — live operational metrics
5. WorkforceOffice — animated AI team view
6. AI Team tab for research tickets and ingestion status

## Known Gaps to Set Expectations For

- Knowledge base: 1 approved record (NitroTrades ICT Silver Bullet) — more coming
- Transcript queue: needs playlist_ingest_worker run to populate video content
- Hermes Telegram: must be on approved chat list to get bot access
