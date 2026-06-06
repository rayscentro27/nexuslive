# MEMORY — Nexus OS Operating Notes

Dense, short, current. Lessons and live state Hermes should assume. Prune aggressively.

## Live State (as of 2026-06-06)
- Nexus OS is live at https://app.goclearonline.cc/app/nexus-os (Netlify site: nexuslive).
- Revenue Hub: live, CRUD works, reads nexus_os_revenue_campaigns.
- Content Studio: live, CRUD works, reads nexus_os_content_items, links to campaigns.
- Approval flow: risky actions insert into owner_approval_queue; events logged to nexus_os_approval_events; notifications table feeds the bell.
- Hermes Chat: live via Netlify → Cloudflare Tunnel (hermes-gateway.goclearonline.cc) → local gateway :8642.
- Telegram: critical/urgent approvals notify; normal-priority is suppressed by policy (TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED=false).

## Patterns / Lessons
- Risky actions are approval-gated by design. Recommend preparing an approval, never executing.
- Cross-module recommendations are the high-value move: read revenue + content + approvals together, recommend the next step.
- Fastest near-term revenue path = affiliate/content campaigns that are closest to launch with the fewest blockers.
- A campaign with high priority but zero linked content is the classic "draft content next" trigger.
- Deterministic rules first, natural language second. The Nexus OS recommendation engine computes structure; Hermes phrases it.

## Do Not
- Do not overfill this file.
- Do not auto-publish, auto-send, or auto-trade.
- Do not claim revenue/results without evidence.
