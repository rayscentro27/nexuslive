# ClawCloud Deployment

Deploy the lightweight Nexus control layer to ClawCloud Run using the `nexus-control-api` service.

This is the cheapest useful remote footprint for Nexus when the goal is:

- Hermes-compatible remote control flow
- project intake over HTTP
- project planning and dispatcher validation
- optional Supabase persistence

This is **not** the full production Nexus stack. It is the remote control node.

## What Gets Deployed

The deployed service is:

- `workflows/ai_workforce/project_orchestrator/nexus_control_api.js`

It exposes:

- `GET /health`
- `GET /project-types`
- `POST /projects`
- `GET /projects/:id`

It depends on:

- `workflows/ai_workforce/workforce_dispatcher.js`
- `workflows/ai_workforce/project_orchestrator/autonomous_project_orchestrator.js`

## Docker Build Source

Use this Dockerfile:

- [workflows/ai_workforce/project_orchestrator/Dockerfile](/Users/raymonddavis/nexus-ai/workflows/ai_workforce/project_orchestrator/Dockerfile)

Build locally if needed:

```bash
cd ~/nexus-ai
docker build -f workflows/ai_workforce/project_orchestrator/Dockerfile -t nexus-control-api .
```

## ClawCloud App Settings

### Port

- expose port `3000`

### Runtime

- use the Dockerfile default `CMD`

### Health Check

Use:

- `GET /health`

Expected healthy response:

```json
{
  "ok": true,
  "service": "nexus-control-api",
  "status": "healthy"
}
```

## Required Environment Variables

These are the minimum required variables:

```env
PORT=3000
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

## Recommended Environment Variables

If you want alerts:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

If you want the control node to have access to your primary inference provider:

Choose only one provider first:

```env
OPENAI_API_KEY=...
```

or

```env
OPENROUTER_API_KEY=...
```

or

```env
GROQ_API_KEY=...
```

Do **not** start by stuffing every fallback provider into the first deployment. Keep the remote node simple.

## First Deployment Checklist

1. Create the ClawCloud Run app.
2. Point it at the repo / image using the Dockerfile above.
3. Set port `3000`.
4. Add the required environment variables.
5. Deploy.
6. Test `GET /health`.
7. Test `GET /project-types`.
8. Send one dry-run project request.

## First Test Request

```bash
curl -X POST https://YOUR-CLAWCLOUD-APP/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "project": {
      "name": "Remote Opportunity Test",
      "project_type": "opportunity_pipeline",
      "objective": "Test remote Nexus planning.",
      "priority": "high",
      "autonomy_mode": "assisted",
      "topics": ["business_opportunities", "crm_automation"],
      "deliverables": ["ranked_opportunities", "operator_brief"],
      "payload": { "since_days": 14, "min_score": 45 }
    },
    "execute": true
  }'
```

Expected result:

- valid plan returned
- dispatcher validation returned
- no live worker execution unless you later enable it intentionally

## Persistence Mode

If you want the remote node to write project plans to Supabase, include:

```json
{
  "persist": true
}
```

in your `POST /projects` body.

This writes to:

- `autonomous_projects`
- `autonomous_project_runs`

Run this migration first:

- [docs/migrations/20260420_autonomous_projects.sql](/Users/raymonddavis/nexus-ai/docs/migrations/20260420_autonomous_projects.sql)

## Recommended First Remote Scope

Start with these project types only:

- `opportunity_pipeline`
- `grant_pipeline`
- `ops_pipeline`

Do not start remote live execution with:

- trading pipelines
- CRM write-like flows
- credit draft flows
- client-facing portal responses

## Suggested Architecture

### ClawCloud

- remote control API
- project intake
- planner
- dispatcher validation
- optional persistence

### Supabase

- source of truth for project and run state
- existing workforce memory tables

### Primary Inference Provider

- one stable paid provider
- not local Ollama

### Mac Mini

- dev machine
- backup tools
- optional fallback worker host

## Practical Recommendation

Treat ClawCloud as the remote command center, not the full autonomous brain.

Use it to:

- receive project requests
- produce job plans
- validate project execution paths
- persist project state

Then gradually add more worker execution behind it once the control layer stays stable.
