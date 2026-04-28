# Autonomous Project Intake

This layer lets Nexus accept a structured project request, convert it into a cross-worker plan, and optionally validate or execute that plan through the existing workforce dispatcher.

## Why This Exists

The workforce already has strong role boundaries. What it was missing was a project-level intake format that can say:

- what the goal is
- which workers are allowed to help
- which outputs are expected
- which steps can run automatically
- which steps must stop for approval

That gap is now filled by:

- `workflows/ai_workforce/project_orchestrator/autonomous_project_orchestrator.js`
- `workflows/ai_workforce/project_orchestrator/nexus_control_api.js`
- `workflows/ai_workforce/project_orchestrator/sample_autonomous_project.json`
- `docs/migrations/20260420_autonomous_projects.sql`

## Supported Project Types

- `grant_pipeline`
- `opportunity_pipeline`
- `content_pipeline`
- `crm_pipeline`
- `credit_pipeline`
- `trading_pipeline`
- `ops_pipeline`
- `custom_multi_role`

## Default Safety Model

- Planning is safe by default.
- `--execute` runs dispatcher validation only unless `--live-dispatch` is also passed.
- Approval-gated jobs are marked `awaiting_approval` unless `--skip-approval-jobs` is explicitly provided after human sign-off.

## Example

```bash
cd ~/nexus-ai/workflows/ai_workforce

node project_orchestrator/autonomous_project_orchestrator.js \
  --project-file project_orchestrator/sample_autonomous_project.json
```

Run the remote-friendly control API locally:

```bash
cd ~/nexus-ai/workflows/ai_workforce
npm run control-api
```

Validate the full cross-worker plan without live execution:

```bash
node project_orchestrator/autonomous_project_orchestrator.js \
  --project-file project_orchestrator/sample_autonomous_project.json \
  --execute
```

Live-dispatch the non-gated jobs:

```bash
node project_orchestrator/autonomous_project_orchestrator.js \
  --project-file project_orchestrator/sample_autonomous_project.json \
  --execute \
  --live-dispatch
```

Persist the project and planned runs to Supabase:

```bash
node project_orchestrator/autonomous_project_orchestrator.js \
  --project-file project_orchestrator/sample_autonomous_project.json \
  --persist
```

## Project Spec Shape

```json
{
  "name": "April Grant + Opportunity Sweep",
  "project_type": "opportunity_pipeline",
  "objective": "Surface the best monetizable opportunities from recent research.",
  "priority": "high",
  "autonomy_mode": "assisted",
  "topics": ["business_opportunities", "crm_automation"],
  "constraints": ["No client PII", "No live trading"],
  "deliverables": ["ranked_opportunities", "operator_brief"],
  "requested_roles": ["research_worker", "opportunity_worker"],
  "payload": {
    "since_days": 14,
    "min_score": 45
  }
}
```

## How To Use It Operationally

Use this as the intake layer for “send Nexus a project” workflows:

1. Human creates a structured project spec.
2. Orchestrator generates a job plan.
3. Dispatcher validates each stage against role, permission, and approval rules.
4. Non-gated work can run automatically.
5. Gated stages stop and wait for human approval.
6. Results can be written to `autonomous_projects` and `autonomous_project_runs`.

## ClawCloud Control API

For a minimal remote Nexus bridge, deploy the control API:

- `GET /health`
- `GET /project-types`
- `POST /projects`
- `GET /projects/:id`

Example request:

```bash
curl -X POST http://localhost:3000/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "project": {
      "name": "April Grant + Opportunity Sweep",
      "project_type": "opportunity_pipeline",
      "objective": "Surface the best monetizable opportunities from recent research.",
      "priority": "high",
      "autonomy_mode": "assisted",
      "topics": ["business_opportunities", "crm_automation"],
      "deliverables": ["ranked_opportunities", "operator_brief"],
      "payload": { "since_days": 14, "min_score": 45 }
    },
    "execute": true,
    "persist": true
  }'
```

Docker build for ClawCloud:

```bash
docker build -f workflows/ai_workforce/project_orchestrator/Dockerfile -t nexus-control-api .
```

## Recommended Rollout

1. Run the SQL migration first.
2. Start with `grant_pipeline` and `opportunity_pipeline`.
3. Use `--execute` without `--live-dispatch` for the first few projects.
4. Only use live dispatch after the plan output looks stable.
5. Keep content, CRM, credit, portal, and trading draft stages behind human approval.
