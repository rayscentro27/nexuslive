# Nexus Architecture Spec

## System Overview
Nexus is an AI operating system for trading, business intelligence, funding readiness, and operator workflows. The architecture is intentionally hybrid: local-first execution for orchestration and control, cloud persistence for memory and reporting, and tiered model providers for cost-aware inference.

## Frontend / Backend Structure
- **Frontend surfaces**
  - Control Center UI for mission control, worker status, and operator actions.
  - Client-facing portal for readiness/funding workflows and progress visibility.
- **Backend services**
  - Python services for orchestration, Telegram handling, scheduling, and monitoring.
  - Worker modules for research, trading, funding intelligence, and CRM operations.
  - API/gateway helpers for provider routing, notification policy, and health checks.

## Supabase Brain Concept
Supabase is the long-term memory and operational brain:
- Stores durable system state, aggregate events, recommendation history, and worker heartbeats.
- Anchors auditability for operator actions and workflow outcomes.
- Serves as cross-worker coordination substrate; no single worker is the source of truth.

## Hermes Orchestration Model
Hermes is the operator-facing orchestrator:
- Inbound: receives human commands/natural language and routes intent safely.
- Coordination: triggers deterministic checks and constrained automation paths.
- Outbound: remains manual/conversational-first with auto-report suppression.

## Infrastructure Roles
- **Mac Mini (primary runtime)**: launcher/process control, Telegram monitor, scheduler, local workflows.
- **Oracle VM**: externally reachable compute/API edge and long-running workloads.
- **Netcup + Ollama**: low-cost local/near-local inference lane for cheap summaries/background workloads.
- **OpenRouter/Gemini/OpenCode**: premium/long-context/dev-class routing lanes.

## Telegram Role
Telegram is an operator control channel, not an autonomous broadcast channel:
- Supports command and natural-language inbound interaction.
- Manual-only outbound policy by default.
- Critical alerts are deduplicated and throttled.

## Model Routing Vision
Routing is capability-first and policy-driven:
- Use premium models for high-context, high-value reasoning.
- Use cheap/local models for summaries and repetitive background tasks.
- Enforce minimum context for mission-critical workflows.
- Preserve graceful fallback without infinite retries.

## Non-goals (Current Phase)
- No destructive schema changes.
- No replacement of core business logic.
- No automatic Telegram broadcast re-enable.
