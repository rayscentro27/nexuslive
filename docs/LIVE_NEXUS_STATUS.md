# Live Nexus Status

Current live operational snapshot for the Nexus stack on Ray's Mac mini.

Last updated: 2026-04-21

Status vocabulary:

- `healthy`: service is running or scheduled normally, with no recent degraded markers
- `scheduled`: interval-driven launchd job that is currently idle between runs
- `degraded`: service is functioning, but recent logs show transient upstream pressure such as rate limits, 5xxs, or retryable network failures
- `external/unmanaged heartbeat`: a worker is writing to `worker_heartbeats`, but it is not part of the current launchd-managed control plane

## Core Runtime

- `com.nexus.orchestrator`: running
- `com.nexus.research-worker`: running
- `ai.openclaw.gateway`: running
- `ai.hermes.gateway`: running
- `com.nexus.ollama`: running
- `com.nexus.signal-router`: running
- `com.nexus.signal-review`: running
- `com.nexus.trading-engine`: running
- `com.nexus.hermes-status`: running
- `com.nexus.mac-mini-worker`: running
- `com.nexus.coordination-worker`: scheduled / interval-driven

## Scheduled / Loaded Workers

These are launchd-loaded and healthy, but may be idle between intervals:

- `com.nexus.opportunity-worker`
- `com.nexus.grant-worker`
- `com.nexus.research-orchestrator-transcript`
- `com.nexus.research-orchestrator-grants-browser`
- `com.nexus.ops-control-worker`
- `com.nexus.coordination-worker`
- `com.nexus.strategy-lab`

## Control Plane

Tracked in Supabase:

- `nexus-orchestrator`: running
- `nexus-research-worker`: running
- `openclaw-gateway`: running
- `hermes-gateway`: running
- `grant-worker`: scheduled / interval-driven
- `opportunity-worker`: scheduled / interval-driven
- `research-orchestrator-transcript`: scheduled / interval-driven
- `research-orchestrator-grants-browser`: scheduled / interval-driven
- `ops-control-worker`: scheduled / interval-driven
- `coordination_worker`: scheduled / interval-driven

Automatic recovery:

- `ops-control-worker` now originates safe `restart_service` actions for automatic workers when:
  - a required launchd label drops out of `launchctl`
  - a persistent worker heartbeat goes stale
- restart actions are cooldown-limited to avoid repeated restart thrash

## AI Employee Snapshot

- `research_worker`: active and healthy
- `grant_worker`: scheduled and healthy
- `opportunity_worker`: scheduled, resumed, and healthy
- `ops_control_worker`: active as the control-plane validator/executor
- `coordination_worker`: scheduled and healthy
- `risk_compliance_worker`: implemented, no dedicated live process right now
- `credit_worker`: not active
- `content_worker`: not active
- `crm_copilot_worker`: not active
- `trading_research_worker`: not active as a dedicated worker process
- `client_portal_assistant`: not active

## Hermes / OpenClaw

- OpenClaw is healthy and locally reachable
- Hermes gateway is running
- Hermes-compatible control requests are enabled through `ops_control_worker`
- Safe machine execution is wired for:
  - `pause_worker`
  - `resume_worker`
  - `restart_service`

## Notes

- `com.nexus.trading-engine` is currently serving local/manual signal intake on port `5000`.
- `DRY_RUN=True` remains the safety boundary, so the running engine stays in demo mode.
- Scheduled one-shot jobs often appear idle in `launchctl` between runs. That is normal.
- `opportunity-worker` was resumed successfully through the new control plane.
- `nexus-research-worker` now self-heals stale queue work conservatively:
  - the stale-state sweep can auto-requeue old `claimed` / `running` jobs
  - auto-requeue only happens when the job is well past threshold and the worker heartbeat is missing or stale
  - requeued jobs are delayed briefly before becoming eligible again to avoid immediate thrash
- `com.nexus.strategy-lab` is now schema-complete and running end-to-end:
  - deterministic scoring is live
  - Hermes review can fall through from local OpenClaw to OpenRouter
  - fallback reviews still persist if AI capacity is temporarily constrained
  - recent resurrected queue items were cleared successfully
- Temporary OpenClaw rate limits are now treated as degraded capacity, not hard pipeline failure.
- `scripts/ai_status.sh` now uses that same vocabulary and can surface `degraded recently` from live runtime evidence rather than treating every transient issue as a failure.
- `coordination_worker` is now launchd-managed on a 15-minute interval and should no longer be treated as an unmanaged background heartbeat once reloaded.
- VS Code Hermes integration is configured through:
  - `hermes.path`
  - `hermes.debugLogs`
