# AI Employee Roles Spec

## Registry Foundation
- Runtime registry module: `lib/ai_employee_registry.py`
- Exposes read-only role metadata and routing previews.
- Default policy posture: conservative (`can_auto_execute=false`, `requires_admin_approval=true`).

## Role IDs
- `ceo_router`
- `credit_ai`
- `funding_ai`
- `grants_ai`
- `business_setup_ai`
- `trading_research_ai`
- `crm_copilot`
- `ops_monitoring_ai`

## Safety Defaults
- `telegram_allowed=false` for all roles by default.
- Exception: `ops_monitoring_ai` allows Telegram only for `critical_only` scope.
- Registry does not activate workers or execute tasks; it is metadata + validation only.

## CEO Router
- Classifies inbound intent and routes to the correct specialist workflow.
- Produces priority-ranked actions and approval queues.

## Credit AI
- Analyzes profile readiness and credit bottlenecks.
- Recommends non-destructive score-improvement actions.

## Funding AI
- Maps readiness to funding path/capital ladder stage.
- Surfaces blockers, lender fit, and next-best funding action.

## Grants AI
- Tracks grant opportunities, constraints, and evidence completeness.
- Produces recommendation briefs for operator review.

## Trading Research AI
- Ingests research and strategy candidates.
- Supports idea scoring and operational digest generation.

## Business Setup AI
- Supports launch planning, entity setup checklists, and opportunity sequencing.
- Avoids policy changes in production routing without approval.

## CRM Copilot
- Tracks engagement, churn risk, intervention urgency, and outreach suggestions.
- Surfaces client-priority queues.

## Ops Monitoring AI
- Aggregates worker health, retries/errors, queue depth, and anomaly indicators.
- Alerts are policy-gated (manual-first, critical exceptions only).

## Helper APIs
- `list_roles()`
- `get_role(role_id)`
- `validate_role_task(role_id, task_type)`
- `role_routing_preview(role_id)`

## Swarm Safety Foundation
- Role-to-role handoffs are constrained by explicit allow-list rules.
- Swarm workflows are preview-only and always approval-gated.
- `can_auto_execute` remains false for all roles in this phase.

## Swarm Scenario Selector (Preview-only)
- Scenario registry module: `lib/swarm_scenarios.py`.
- Scenarios are predefined and operator-selectable for safe planning previews only.
- Supported scenario ids:
  - `funding_onboarding`
  - `credit_remediation`
  - `grant_research`
  - `ops_incident_triage`
  - `business_setup_readiness`
  - `trading_research_review`
- Every scenario is hard-pinned to:
  - `approval_required=true`
  - `execution_mode=preview_only`
  - `can_execute=false`
