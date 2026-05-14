# Launchd / Cron / Scheduler Forensics

Generated: 2026-05-14

## Launchd Audit (User LaunchAgents)
- Confirmed active labels: `com.raymonddavis.nexus.telegram`, `com.raymonddavis.nexus.scheduler`, `ai.hermes.gateway`, `ai.nexus.control-center`, `com.nexus.orchestrator`, `com.nexus.research-worker`, `com.nexus.ollama`, others.
- Removed deprecated/summary-prone agents:
  - `com.nexus.opportunity-worker.plist`
  - `com.nexus.grant-worker.plist`
  - `com.nexus.research-orchestrator-transcript.plist`
  - `com.nexus.research-orchestrator-grants-browser.plist`

## Cron Audit (`crontab -l`)
- Active periodic jobs include `memory_worker`, `optimization_worker`, `monitoring_worker`, `autonomy_worker`, `coordination_worker`, `scheduler_worker`, `readiness_worker`, `improvement_worker`, `empire_worker`, `provider_health_worker`, `research_processing_worker`, `opportunity_research_worker`.
- Two legacy Nexus One summary lines already commented out (`DISABLED telegram-summary-spam-removal`).

## Scheduler Forensics
- `operations_center/scheduler.py` sends through `lib.hermes_gate.send` (`_notify`).
- Event types observed for scheduler notifications include `daily_digest` and `critical_ops_alert`.
- Auto-summary suppression already present, but allowlist hardening was strengthened in `lib/hermes_gate.py`.

## Risky Fanout Paths Identified
- Worker-local `sendMessage` calls in multiple workflow modules bypass central gate.
- Opportunity/grant brief generators were explicit spam vectors and are now policy-denied.
