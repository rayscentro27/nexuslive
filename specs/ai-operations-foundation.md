# AI Operations Foundation Spec

## Goal
Establish non-destructive observability foundations for AI operations without changing core business logic.

## Coverage Areas
- AI task cost tracking (event-level, provider/model scoped)
- Workflow execution metrics (duration, outcome, retries)
- Model usage tracking (task class -> provider/model)
- Retry/error analytics (error class, retry stage)
- Worker health tracking (heartbeat-oriented summaries)

## Initial Implementation Strategy
- Use additive helper modules.
- Reuse existing aggregate event stores where possible.
- Avoid schema changes in this phase.

## Data Semantics
- Write compact, queryable summaries into event streams.
- Keep sensitive prompt payloads out of telemetry.
- Preserve deterministic identifiers for dedup and trend grouping.

## Rollout Policy
- Start with passive telemetry helpers.
- Integrate selectively into high-value paths first.
- Validate with lightweight scripts before broad adoption.

## AI Ops Dashboard Purpose
- Provide a read-only operational snapshot for AI routing and safety posture.
- Help operators verify runtime model/Telegram policy configuration quickly.
- Surface routing decisions and recent telemetry without mutating system state.

## Endpoint Contract
- `GET /api/admin/ai-ops/status`
- Returns:
  - `model_config` (default provider/model/context)
  - `telegram_mode` (enabled/manual_only/auto_reports_enabled)
  - `routing_preview` (selected task classes)
  - `worker_health_summary` (counts + recent rows)
  - `telemetry` (recent retry/error + model usage summaries)
  - `read_only=true`

## Read-only Boundary
- No write endpoints are introduced for AI Ops dashboard controls.
- No job triggers or outbound notifications are sent by dashboard reads.
- Dashboard consumers must treat output as diagnostics only.

## Deferred Future Controls
- Provider override toggles
- Runtime circuit-breaker reset controls
- On-demand workflow kill/restart controls
- Telemetry retention controls

These are intentionally deferred to avoid accidental production mutation risk.

## Operator Controls (Current Additive Scope)
- Admin-scoped toggle controls are exposed via Control Center AI OPS panel.
- Backed by `POST /api/admin/ai-ops/telegram-mode`.
- Intended use: adjust Telegram safety flags only (`TELEGRAM_ENABLED`, `TELEGRAM_MANUAL_ONLY`, `TELEGRAM_AUTO_REPORTS_ENABLED`).
- Every write action is logged server-side with actor/ip metadata.
- No model secret mutation, no schema mutation, no workflow execution triggers.

## AI Employee Registry Surface
- Read-only admin endpoint: `GET /api/admin/ai-ops/roles`
- Purpose: expose role policy metadata and routing previews for operator audit.
- UI section: `AI Employees` in AI OPS panel.
- No autonomous activation is permitted from this surface.

## Swarm Orchestration Preview Surface
- Read-only admin endpoint: `GET /api/admin/ai-ops/swarm-preview`
- Purpose: show safe role handoff plan before any execution.
- Output includes initiating role, delegated roles, task sequence, model class by role,
  approval requirement, risk level, blocked/allowed status, and decision reasons.
- Execution remains disabled (`can_execute=false`) by policy.

## Swarm Scenario Selector Surface
- Read-only admin endpoints:
  - `GET /api/admin/ai-ops/swarm-scenarios`
  - `GET /api/admin/ai-ops/swarm-scenario-preview?scenario_id=...`
- Purpose: select a predefined business workflow and inspect a role/model/risk preview.
- Scenario preview output includes:
  - scenario metadata (`scenario_id`, `display_name`, `description`)
  - initiating role + delegated roles
  - role sequence with blocked/allowed reasons
  - approval/risk posture
  - hard safety flags (`execution_mode=preview_only`, `can_execute=false`)
- Both endpoints require admin auth and are diagnostics-only.

## Smoke Test Runner
- Command: `scripts/smoke_ai_ops.sh`
- Runs the full AI Ops/Hermes infrastructure validation suite in one pass.
- Uses fail-fast behavior (stops on first failure).

Run this smoke suite:
- before restart
- before git commit
- after AI Ops changes
