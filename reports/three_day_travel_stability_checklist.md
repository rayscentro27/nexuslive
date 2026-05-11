# 3-Day Travel Stability Checklist

Date: 2026-05-11
Window: next 72 hours

## Access + Recovery
- [ ] Chrome Remote Desktop connection verified from Surface
- [ ] Surface browser access to Nexus admin routes verified
- [ ] iPhone PWA login and relaunch behavior verified
- [ ] Emergency restart docs reachable from phone and Surface

## Mobile/Admin Validation
- [ ] Admin dashboard usable on iPhone without horizontal clipping
- [ ] Client dashboard usable on iPhone with clear CTA visibility
- [ ] Workforce Operations Center readable on iPhone
- [ ] Admin auth protections still enforce unauthenticated `403`

## Operating Continuity
- [ ] Telegram operator flow responds to status/next-step prompts
- [ ] Email reporting path sends from configured runtime
- [ ] Invite flow endpoints and copy remain reachable
- [ ] Knowledge review queue is reachable and updated

## Daily Cadence During Travel
- Morning: Telegram status + admin dashboard quick check
- Midday: Workforce/timeline glance + queue check
- Evening: CEO summary + blocker capture + next-day priorities

## Emergency Rollback Sequence
1. Verify remote access (SSH/CRD/Tailscale path)
2. Restart critical services only (telegram/scheduler/control-center/orchestrator/research-worker)
3. Revalidate Telegram, admin auth, workforce route, and email report path
4. Defer optional services until baseline is stable
