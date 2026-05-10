# Nexus Operator Validation Checklist

Purpose: validate Nexus as a real-world operator platform without enabling unsafe automation.

Safety baseline (must remain unchanged):
- `SWARM_EXECUTION_ENABLED=false`
- `HERMES_SWARM_DRY_RUN=true`
- `HERMES_CLI_EXECUTION_ENABLED=false`
- `HERMES_CLI_DRY_RUN=true`
- `TRADING_LIVE_EXECUTION_ENABLED=false`
- `TELEGRAM_AUTO_REPORTS_ENABLED=false`
- `TELEGRAM_FULL_REPORTS_ENABLED=false`
- `hooks_auto_accept=false`
- `HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false`

## 1) Onboarding
- [ ] Start as brand-new user with no prior context
- [ ] Confirm first screen explains what Nexus does in plain language
- [ ] Confirm next step is obvious within 10 seconds
- [ ] Confirm trust signals are visible (beta status, disclaimers, non-guarantee language)
- [ ] Confirm operator can reach dashboard without backend help
- [ ] Record friction points and unclear wording

## 2) Invite Flow
- [ ] Send real beta invite to controlled test inbox
- [ ] Verify subject line and sender credibility
- [ ] Verify signup link works from desktop and phone
- [ ] Verify disclaimer copy is visible and readable
- [ ] Verify waived-access/beta language preserved
- [ ] Verify invite-to-dashboard completion without dead ends

## 3) Mobile Install
- [ ] iPhone: open app, verify install prompt/behavior
- [ ] iPhone: verify dashboard renders correctly
- [ ] Surface: open app, verify responsive scaling
- [ ] Surface: verify no clipped controls or hidden CTA buttons
- [ ] Confirm core pages usable without zoom gymnastics

## 4) Dashboard Usability
- [ ] Confirm executive view is legible at a glance
- [ ] Confirm key status cards surface useful operational state
- [ ] Confirm no misleading or fake activity indicators
- [ ] Confirm empty states are understandable and actionable
- [ ] Confirm load time and interaction feel acceptable

## 5) Hermes Usability
- [ ] Operate only through Telegram and operator-facing reports
- [ ] Confirm internal-first responses remain consistent
- [ ] Confirm responses are concise and decision-usable
- [ ] Confirm no unsafe action is auto-executed

## 6) Knowledge Intake
- [ ] Submit real email knowledge input
- [ ] Verify parser extracts sender, links, and category
- [ ] Verify item appears in review queue
- [ ] Verify review workflow moves item through expected statuses
- [ ] Verify retrieval/readout is useful for executive decisions

## 7) CEO Reports
- [ ] Generate CEO-style report
- [ ] Confirm report clarity, brevity, and decision support quality
- [ ] Confirm metrics/context are understandable without engineering translation
- [ ] Confirm no secrets are exposed

## 8) Workforce Center
- [ ] Verify unauthorized access returns `403`
- [ ] Verify authorized access returns `200`
- [ ] Verify worker states and queue summaries are meaningful
- [ ] Verify timeline/activity sections are useful and not noisy
- [ ] Verify mobile readability and interaction on iPhone/Surface
- [ ] Verify no performance regressions versus baseline

## 9) Remote Access
- [ ] Confirm operator can access dashboard/workforce tools remotely
- [ ] Confirm auth process is reliable and documented
- [ ] Confirm recovery visibility is available during partial outages
- [ ] Confirm restart/runbook steps are discoverable by non-engineer operator

## 10) Travel Readiness
- [ ] Simulate Mac mini inaccessible scenario
- [ ] Operate only from iPhone + Surface
- [ ] Validate continuity for Telegram, dashboard, and reports
- [ ] Validate emergency operating steps are clear and sufficient
- [ ] Capture blockers that would prevent same-day operations

## Evidence Log (fill during pass)
- Date/time:
- Operator:
- Environment:
- Completed checks:
- Failures/blockers:
- Follow-up fixes:
