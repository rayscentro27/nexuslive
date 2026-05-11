# Nexus AI Workforce

The Nexus AI Workforce is a collection of specialized AI employee modules, each with a defined role, tool boundary, and memory access policy. All workers are **research-only** — no live trading, no broker connections, no client PII in automated flows.

## Directory Structure

```
workflows/ai_workforce/
├── env.js                          ← Shared dotenv loader (resolves ../../.env)
├── workforce_registry.js           ← Maps role IDs to implementation modules
├── workforce_roles.js              ← All 10 role definitions (mission, I/O, tools)
├── workforce_dispatcher.js         ← Routes job payloads to workers, enforces permissions
├── project_orchestrator/           ← Structured project intake → cross-worker plans
├── workforce_permissions.js        ← PERM flags, BLOCKED_PERMS, per-role grants
├── workforce_memory_map.js         ← Table × Role access matrix (READ/WRITE/DRAFT/NONE)
├── workforce_job_types.js          ← JOB_TYPE constants, ROLE_JOB_TYPES, APPROVAL gates
│
├── grant_worker/                   ← ✅ Implemented
│   ├── grant_worker.js
│   ├── grant_normalizer.js
│   ├── grant_scoring.js
│   └── grant_brief_generator.js
│
├── opportunity_worker/             ← ✅ Implemented
│   ├── opportunity_worker.js
│   ├── opportunity_normalizer.js
│   ├── opportunity_scoring.js
│   └── opportunity_brief_generator.js
│
├── risk_compliance_worker/         ← ✅ Implemented
├── trading_research_worker/        ← 🔶 Partial
├── credit_worker/                  ← 🔸 Stub
├── content_worker/                 ← 🔸 Stub
├── crm_copilot_worker/             ← 🔸 Stub
├── ops_monitoring_worker/          ← 🔸 Stub
└── client_portal_assistant/        ← ⬜ Planned
```

## The 10 AI Employees

| # | Role ID | Name | Status |
|---|---------|------|--------|
| 1 | `research_worker` | Research Worker | ✅ Implemented |
| 2 | `grant_worker` | Grant Worker | ✅ Implemented |
| 3 | `opportunity_worker` | Opportunity Worker | ✅ Implemented |
| 4 | `credit_worker` | Credit Worker | 🔸 Stub |
| 5 | `content_worker` | Content Worker | 🔸 Stub |
| 6 | `crm_copilot_worker` | CRM Copilot Worker | 🔸 Stub |
| 7 | `client_portal_assistant` | Client Portal Assistant | ⬜ Planned |
| 8 | `trading_research_worker` | Trading Research Worker | 🔶 Partial |
| 9 | `risk_compliance_worker` | Risk & Compliance Worker | ✅ Implemented |
| 10 | `ops_monitoring_worker` | Ops & Monitoring Worker | 🔸 Stub |

## Using the Dispatcher

```bash
cd ~/nexus-ai/workflows/ai_workforce

# List all roles and their status
node workforce_dispatcher.js --list-roles

# List allowed job types for a role
node workforce_dispatcher.js --list-jobs grant_worker

# Dispatch a job (dry run — validates only, no execution)
node workforce_dispatcher.js --role grant_worker --job grant_scan --dry-run

# Dispatch a grant scan (live write to Supabase + Telegram)
node workforce_dispatcher.js --role grant_worker --job grant_scan --since 30

# Dispatch an opportunity scan
node workforce_dispatcher.js --role opportunity_worker --job business_scan --since 14

# Dispatch with score filter
node workforce_dispatcher.js --role opportunity_worker --job opportunity_scan --min-score 50

# Build a project-level plan for multiple workers
node project_orchestrator/autonomous_project_orchestrator.js \
  --project-file project_orchestrator/sample_autonomous_project.json
```

## Running Workers Directly

Workers can also be run standalone:

```bash
# Grant Worker
node grant_worker/grant_worker.js --dry-run
node grant_worker/grant_worker.js --since 30 --min-score 40

# Opportunity Worker
node opportunity_worker/opportunity_worker.js --dry-run
node opportunity_worker/opportunity_worker.js --since 14 --topic crm_automation

# Research Worker (via orchestrator)
node ../autonomous_research_supernode/research_orchestrator.js
```

## Dispatch Flow

```
Job Request
    │
    ▼
workforce_dispatcher.js
    │
    ├── 1. Validate role exists in registry
    ├── 2. Check role is runnable (not planned/stub)
    ├── 3. Verify job type is allowed for this role
    ├── 4. Check approval gate (APPROVAL_REQUIRED_JOBS)
    ├── 5. Verify role has required permissions for job
    │
    ▼
Worker Module (dynamically imported)
    │
    ├── Loads research_artifacts from Supabase (READ)
    ├── Normalizes + scores data (heuristic, no AI calls)
    ├── Writes output table (WRITE — grant_opportunities, business_opportunities, etc.)
    └── Sends Telegram brief alert
```

## Autonomous Project Intake

For “send Nexus a project” workflows, use the project orchestrator:

```bash
cd ~/nexus-ai/workflows/ai_workforce

node project_orchestrator/autonomous_project_orchestrator.js \
  --project-file project_orchestrator/sample_autonomous_project.json
```

This layer:

- validates a structured project spec
- converts the request into a cross-worker execution plan
- can optionally run dispatcher validation for every stage
- can optionally persist project/run rows to Supabase
- still respects approval gates for sensitive jobs

## Permission System

All roles have explicit permission grants defined in `workforce_permissions.js`. Eight permissions are permanently blocked for all roles:

- `CLIENT_PII_DIRECT` — no direct access to client PII
- `BROKER_API` — no broker connections
- `ORACLE_SSH` — no Oracle VM access
- `BILLING_CONTROL` — no payment controls
- `SUPERADMIN` — no admin overrides
- `LIVE_TRADE_EXECUTION` — no live trade execution
- `AUTO_PUBLISH_CONTENT` — content requires human review
- `AUTO_EXECUTE_CRM` — CRM changes require human approval

## Approval-Required Jobs

These job types are blocked by the dispatcher unless `skipApprovalGate: true` is explicitly passed (after human sign-off):

| Job Type | Role | Reason |
|----------|------|--------|
| `credit_dispute_draft` | credit_worker | Touches client credit profile |
| `trading_strategy_draft` | trading_research_worker | Draft investment logic |
| `content_social_draft` | content_worker | Public-facing content |
| `content_newsletter_draft` | content_worker | Email to subscribers |
| `crm_suggestion_generate` | crm_copilot_worker | CRM workflow changes |
| `portal_query_respond` | client_portal_assistant | Client-facing response |

## Memory Map (Table Access)

See `workforce_memory_map.js` for the full 14-table × 10-role access matrix. Key rules:

- `research_artifacts` — ResearchWorker writes; most others read; ClientPortalAssistant has no access
- `business_opportunities` — OpportunityWorker writes; CRMCopilot + ClientPortal can read
- `grant_opportunities` — GrantWorker writes; ClientPortal can read
- `reviewed_signal_proposals` — TradingResearchWorker can draft; RiskWorker reviews
- `approval_queue` — RiskComplianceWorker writes approvals/rejections only
- `risk_decisions` — RiskComplianceWorker writes; TradingResearchWorker reads

## Prerequisites

1. `.env` must have `SUPABASE_URL`, `SUPABASE_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`)
2. `.env` should have `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` for alerts (optional)
3. Run SQL schemas before first production write:
   - `docs/grant_opportunities.sql`
   - `docs/business_opportunities.sql`
   - `docs/research_briefs.sql`

## Autonomous Opportunity Engine (Mac Mini)

A cross-table opportunity layer is available at:
`workflows/ai_workforce/autonomous_opportunity_engine/`

Safe test run:

```bash
cd ~/nexus-ai/workflows/ai_workforce
node autonomous_opportunity_engine/autonomous_opportunity_engine.js --dry-run --since 30 --limit 20
```

Focused scans:

```bash
node autonomous_opportunity_engine/autonomous_opportunity_engine.js --job-type grant_opportunity_scan --dry-run
node autonomous_opportunity_engine/autonomous_opportunity_engine.js --job-type service_gap_scan --dry-run
```

Optional persistence (`business_opportunities` + `grant_opportunities`) is off by default and only enabled with `--persist`.
