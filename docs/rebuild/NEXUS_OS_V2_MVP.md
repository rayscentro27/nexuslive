# Nexus OS v2 — MVP Scope

The smallest system that genuinely runs Communication + Monetization + Automation and
produces daily proof. Everything else waits.

## In scope (MVP)
1. **Nexus OS dashboard** — 7 tabs, all reading `nexus_events`.
2. **Hermes Advisor** — status + chat with honest snapshot fallback (no fake "live").
3. **TheChoseone executor commands** — approve/reject/status, guarded, read-only default.
4. **Facebook publisher** — queue item → approve → dry-run → publish (proven path + non-expiring token).
5. **Social queue** — backed by the ledger, not a JSONL/manifest.
6. **Creative Studio v1** — angle-varied content + quality/compliance gate.
7. **$97 offer funnel** — offer → content → checklist CTA → $97 review → ladder.
8. **Business opportunity generator** — 5 scored opportunities + best-plan.
9. **Oanda demo executor v1** — consumes signal-router, SL/TP required, $500 loss cap.
10. **Event ledger** — `nexus_events` (the spine).
11. **Daily proof report** — one honest summary projection.

## Out of scope (defer)
- Full CRM, complex client portal.
- Advanced multi-agent swarm.
- Full trading tournament.
- Paid ads, Stripe automation, any money movement.
- **Instagram publishing** until media/container v1 is ready.
- Live/funded trading (ever, without explicit approval).

## Definition of done (MVP)
- One scheduler runs the overnight loop; no duplicate jobs.
- A real Facebook post publishes end-to-end from the dashboard-approved queue.
- A demo trade executes (or cleanly reports "no safe signal") with the $500 cap enforced.
- War Room sends **one** guarded daily summary, never a burst.
- Proof Log shows every action as a ledger event.
