# Hermes Workflows Spec

## Workflow Lifecycle
1. Intake: operator message or scheduled task arrives.
2. Normalize/classify: map input to deterministic command or reasoning task.
3. Plan execution: resolve model/task class and required context budget.
4. Execute: run deterministic checks or model call with bounded retries.
5. Record: persist outcome/telemetry to Supabase-backed event store.
6. Respond: direct response to operator (manual channel), or suppress auto-report.

## Job Queue Behavior
- Queue-backed work is asynchronous and idempotent where possible.
- Work items include source, task type, timestamps, and status transitions.
- Duplicate jobs should be collapsed or marked superseded when semantically identical.

## Orchestrator Behavior
- Hermes routes by intent and safety policy.
- Deterministic intents run local checks first.
- Reasoning intents run through model routing with minimum-context enforcement.
- Coding intents route to external coding tools; Hermes provides briefing only.

## Retry Rules
- Bounded retries only; no unbounded loops.
- Prefer fail-fast on config/auth errors.
- Retry transient transport/timeouts with short backoff.
- Persist error class and count for diagnostics.

## Circuit Breaker Concepts
- Error storms trigger temporary suppression windows.
- Repeated identical failures should emit at most one operator alert in cooldown window.
- Recovery clears suppression state after successful checks.

## Manual-only Communication Rules
- Background worker completion does not auto-message Telegram.
- User-initiated prompts always receive direct responses.
- Automated outbound summaries remain suppressed unless explicitly enabled.
- Critical alerts may bypass suppression with dedup + cooldown.

## Safety Boundaries
- Do not mutate auth, RLS, billing/funding scoring, or production routing without explicit approval.
- Prefer additive modules/specs over deep rewrites.
- Keep existing command compatibility stable.

## Swarm Scenario Planning Mode
- Hermes AI Ops supports scenario planning previews only in this phase.
- Operators choose a predefined scenario in Control Center AI OPS (`Swarm Scenario`).
- Selection renders a read-only preview of involved AI employees, ordering, and risk gates.
- No autonomous execution, no outbound Telegram broadcast, and no client-facing workflow mutation are permitted from this surface.
