# Manual Live Validation Next Steps

Date: 2026-05-10
Purpose: final production-side manual validation checklist for mobile/admin/operator readiness.

## 1) iPhone PWA Install
- [ ] Open `https://nexus.goclearonline.com` in Safari
- [ ] Tap Share -> Add to Home Screen
- [ ] Confirm home-screen icon appears and launches app
- [ ] Confirm login persists across close/reopen
- [ ] Confirm logout/login works cleanly

## 2) Client Dashboard Test
- [ ] Log in as client user
- [ ] Confirm onboarding text is clear and actionable
- [ ] Confirm dashboard cards render without clipping
- [ ] Confirm funding roadmap section is readable on mobile
- [ ] Confirm primary CTAs are visible without excessive scrolling

## 3) Admin Dashboard Test
- [ ] Log in with admin role account
- [ ] Confirm protected admin routes are accessible when authenticated
- [ ] Confirm unauthorized behavior is blocked for non-admin session
- [ ] Confirm queue/alerts/snapshot panels are readable on phone
- [ ] Confirm admin navigation is touch-friendly

## 4) Workforce Operations Center Mobile Test
- [ ] Open `/admin/workforce-operations` on iPhone
- [ ] Confirm key cards load and layout remains legible
- [ ] Confirm worker state/queue summary blocks are meaningful
- [ ] Confirm timeline/recent activity sections are readable
- [ ] Confirm no fake activity indicators are shown

## 5) Real Invite Email Test
- [ ] Send one controlled beta invite to real inbox
- [ ] Verify subject/sender trust signals
- [ ] Verify signup link opens and completes flow
- [ ] Verify disclaimer visibility and waived beta wording
- [ ] Verify invited user reaches dashboard

## 6) Real Knowledge Email Test
- [ ] Send real knowledge intake email
- [ ] Verify parser captures sender/subject/links/category
- [ ] Verify record appears in review queue
- [ ] Verify review action updates status correctly
- [ ] Verify Hermes retrieval/CEO summary usefulness

## 7) Surface Remote Access Test
- [ ] Access Nexus from Surface browser
- [ ] Confirm client and admin pages render correctly
- [ ] Confirm auth/session persistence after refresh
- [ ] Confirm workforce center usability on Surface resolution
- [ ] Confirm no major keyboard/mouse interaction issues

## 8) Chrome Remote Desktop Test
- [ ] Launch remote session to Mac mini
- [ ] Confirm stable connection and acceptable latency
- [ ] Confirm ability to reach ops dashboards/tools
- [ ] Confirm session recovery after temporary disconnect
- [ ] Confirm restart/runbook links are reachable

## 9) VS Code Remote SSH Test
- [ ] Connect to target host from Surface via Remote SSH
- [ ] Confirm repository access and command execution
- [ ] Confirm logs/check scripts are readable
- [ ] Confirm no credential prompts block workflow unexpectedly
- [ ] Confirm recovery steps documented if SSH fails

## 10) Oracle / Netlify / Supabase / GitHub Access Test
- [ ] Oracle console login/access works
- [ ] Netlify dashboard access works
- [ ] Supabase project access works
- [ ] GitHub repo/branch access works
- [ ] Confirm operator can inspect status without privileged changes

## Completion Criteria
- [ ] All checklist blocks reviewed
- [ ] Any blockers documented with severity and workaround
- [ ] GO / NO-GO decision recorded for live operator readiness
