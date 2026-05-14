# Repo Telegram Sender Forensics (`nexus-ai` + `nexuslive`)

Generated: 2026-05-14

## High-Impact Senders (Direct Telegram API)
- `workflows/ai_workforce/opportunity_worker/opportunity_brief_generator.js` → `sendOpportunityBriefAlert` → event `opportunity_summary` (auto). Prior state: bypass policy. Action: **gated+denied**.
- `workflows/ai_workforce/grant_worker/grant_brief_generator.js` → `sendGrantBriefAlert` → event `grant_summary` (auto). Prior state: bypass policy. Action: **gated+denied**.
- `workflows/autonomous_research_supernode/telegram_brief_alert.js` and `telegram_research_alert.js` → summary/brief fanout. Action: keep code but blocked by policy allowlist/default deny.
- `services/nexus-orchestrator/src/alerts/emit.js`, `services/nexus-research-worker/src/lib/telegram.js`, several lab/worker modules have direct send path. Action: **gate/remove in follow-up** (see failing static test).

## Primary Conversational Sender
- `telegram_bot.py` uses controlled routes and policy layers; should remain.

## Policy Enforcement State
- Python policy: `lib/telegram_notification_policy.py` updated with explicit blocked types (including `opportunity_summary`, `grant_summary`, `topic_brief`, `run_summary`).
- JS policy: `workflows/lib/telegram_notification_policy.js` similarly updated.
- `nexuslive` did not have this policy file; added `workflows/lib/telegram_notification_policy.js`.

## Recommendation Matrix
- Keep: conversational replies, critical alerts, explicit operator-requested digest, coding completion ack.
- Gate: all remaining operational/worker paths.
- Remove: legacy auto brief and auto summary fanout architecture.
