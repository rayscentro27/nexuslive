# Nexus AI Workforce Architecture

## Overview

The Nexus AI Workforce is a modular, role-based system of specialized AI agents operating within the Nexus AI platform. Each agent ("AI Employee") is assigned a fixed role, bounded tool set, and explicit database access permissions. No agent can exceed its declared scope.

**Core principles:**

- **Additive only** — workers never modify or delete research_artifacts or source data
- **Research only** — no live trading, no broker API calls, no client PII in automated flows
- **Heuristic scoring** — GrantWorker and OpportunityWorker use deterministic keyword scoring (no AI API calls on ingested content)
- **Silent failure** — missing Supabase tables cause logged warnings, not crashes
- **Human gates** — approval-required jobs are blocked by the dispatcher until human sign-off

---

## System Diagram

```
                        ┌─────────────────────────────┐
                        │     Job Source               │
                        │  (CLI / Queue / Cron)        │
                        └────────────┬────────────────┘
                                     │ { role, job, payload }
                                     ▼
                        ┌─────────────────────────────┐
                        │   workforce_dispatcher.js    │
                        │                             │
                        │  1. Role validation         │
                        │  2. Job type check          │
                        │  3. Approval gate           │
                        │  4. Permission check        │
                        └────────────┬────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  ResearchWorker  │  │   GrantWorker    │  │ OpportunityWorker│
   │  research_orches │  │  grant_worker.js │  │ opportunity_w.js │
   └────────┬─────────┘  └───────┬──────────┘  └────────┬─────────┘
            │                    │                       │
            ▼                    ▼                       ▼
   ┌────────────────────────────────────────────────────────────────┐
   │                    Supabase (PostgREST)                        │
   │  research_artifacts │ grant_opportunities │ business_opps      │
   │  research_claims    │ research_briefs     │ approval_queue     │
   │  research_briefs    │ risk_decisions      │ reviewed_signals   │
   └────────────────────────────────────────────────────────────────┘
            │
            ▼
   ┌──────────────────┐
   │   Telegram Bot   │
   │  @Nexustelegraha │
   └──────────────────┘
```

---

## Layer Architecture

### Layer 1 — Research Ingestion (ResearchWorker)
The base layer. All downstream workers depend on data produced here.

```
YouTube / Websites / Manual JSON
        │
        ▼
  research_orchestrator.js
        │
        ├── Transcript lane  (yt-dlp → transcript_extractor.js)
        ├── Browser lane     (Comet adapter → browser_researcher.js)
        └── Manual lane      (JSON files → manual_ingestion.js)
        │
        ▼
  OpenClaw /v1/chat/completions
  (claim extraction + topic classification)
        │
        ▼
  Supabase: research_artifacts, research_claims, research, research_clusters
```

### Layer 2 — Specialization Workers (Grant, Opportunity, Trading, Credit, Content)
Process Layer 1 output into domain-specific insights. No AI calls in GrantWorker/OpportunityWorker — heuristic only.

```
research_artifacts
        │
        ├── topic = 'grant_research'         → GrantWorker → grant_opportunities
        ├── topic IN ('business_opp','crm')  → OpportunityWorker → business_opportunities
        ├── topic IN ('trading','signals')   → TradingResearchWorker → reviewed_signal_proposals
        └── topic = 'credit_repair'          → CreditWorker → (draft review)
```

### Layer 3 — Risk & Compliance (RiskComplianceWorker)
Reviews trading proposals from Layer 2 before any action is taken.

```
reviewed_signal_proposals (DRAFT)
        │
        ▼
  RiskComplianceWorker
        │
        ├── Risk rules check (drawdown, position size, exposure)
        └── approval_queue → APPROVED / REJECTED → risk_decisions
```

### Layer 4 — Content & Communication (ContentWorker, CRMCopilotWorker, ClientPortalAssistant)
Content generation and client-facing communication. All output is DRAFT — human review required before publish.

```
research_briefs + business_opportunities
        │
        ▼
  ContentWorker → content drafts (social, newsletter) — DRAFT ONLY
  CRMCopilotWorker → CRM workflow suggestions — DRAFT ONLY
  ClientPortalAssistant → client portal query answers — SCOPED READ
```

### Layer 5 — Operations (OpsMonitoringWorker)
Cross-cutting concern. Monitors system health, queue depth, and service status.

```
All Supabase tables (counts only)
        │
        ▼
  OpsMonitoringWorker → health reports → Telegram alerts
```

---

## Workforce Scaffold Files

| File | Purpose |
|------|---------|
| `workforce_registry.js` | Maps role IDs → module paths + runner function names |
| `workforce_roles.js` | Full role definitions (mission, tasks, I/O, tools) |
| `workforce_dispatcher.js` | Routes jobs, enforces permission + approval gates |
| `workforce_permissions.js` | PERM flags, BLOCKED_PERMS, role permission grants |
| `workforce_memory_map.js` | Table × Role access matrix |
| `workforce_job_types.js` | JOB_TYPE constants, per-role allowed jobs, approval gates |

---

## Dispatch Model

A job request flows through the dispatcher in this exact sequence:

1. **Role lookup** — Is the role registered? Is the module runnable (not stub/planned)?
2. **Job validation** — Is this job type allowed for this role?
3. **Approval gate** — Is the job in `APPROVAL_REQUIRED_JOBS`? Block unless `skipApprovalGate=true`.
4. **Permission check** — Does the role have all required permissions for this job?
5. **Dynamic import** — Import the worker module by path from the registry.
6. **Invoke runner** — Call the exported runner function with the job payload.
7. **Result + timing** — Return `{ role, job, result, elapsed_ms }`.

---

## Permission Architecture

### Blocked Permanently (All Roles)

| Permission | Reason |
|-----------|--------|
| `CLIENT_PII_DIRECT` | Client data stays in CRM; no direct AI access |
| `BROKER_API` | No broker connections from any AI agent |
| `ORACLE_SSH` | Oracle VM managed from Windows only |
| `BILLING_CONTROL` | No payment or subscription actions |
| `SUPERADMIN` | No admin overrides by any AI agent |
| `LIVE_TRADE_EXECUTION` | System is DRY_RUN; no live execution |
| `AUTO_PUBLISH_CONTENT` | All content requires human review |
| `AUTO_EXECUTE_CRM` | CRM changes require human approval |

### Approval-Required Jobs

These jobs are blocked by the dispatcher unless `skipApprovalGate: true` is explicitly passed after a human has reviewed and approved the intent:

| Job | Role | Why It's Gated |
|-----|------|----------------|
| `credit_dispute_draft` | CreditWorker | Touches client credit profile |
| `trading_strategy_draft` | TradingResearchWorker | Draft investment logic |
| `content_social_draft` | ContentWorker | Public-facing content |
| `content_newsletter_draft` | ContentWorker | Outbound email to subscribers |
| `crm_suggestion_generate` | CRMCopilotWorker | Workflow changes to CRM |
| `portal_query_respond` | ClientPortalAssistant | Client-facing responses |

---

## Memory Map Summary

Access levels: **WRITE** > **DRAFT** > **READ** > **NONE**

| Table | ResearchW | GrantW | OpportunityW | CreditW | ContentW | CRMCopilot | ClientPortal | TradingW | RiskW | OpsW |
|-------|-----------|--------|-------------|---------|----------|------------|-------------|----------|-------|------|
| research_artifacts | W | R | R | R | R | R | — | R | R | R |
| research_claims | W | R | R | R | — | R | — | R | R | R |
| research_briefs | W | W | W | D | R | R | R | W | R | R |
| research_clusters | W | R | R | R | R | R | — | R | — | — |
| research_relationships | W | R | R | — | — | — | — | R | — | — |
| research | W | — | — | — | R | — | — | — | — | — |
| grant_opportunities | — | W | — | — | R | — | R | — | — | R |
| business_opportunities | — | — | W | — | R | R | R | — | — | R |
| reviewed_signal_proposals | — | — | — | — | — | — | — | D | R | R |
| approval_queue | — | — | — | — | — | — | — | — | W | R |
| risk_decisions | — | — | — | — | — | — | — | R | W | R |

W=WRITE, D=DRAFT, R=READ, —=NONE

---

## Development Roadmap

### ✅ Implemented
- ResearchWorker (transcript + manual + browser lanes)
- GrantWorker (grant_opportunities, scoring, Telegram brief)
- OpportunityWorker (business_opportunities, niche detection, scoring, Telegram brief)
- RiskComplianceWorker (risk_decisions, approval_queue writes)
- Workforce scaffold (dispatcher, registry, permissions, memory map, job types, roles)

### 🔶 Partial
- TradingResearchWorker — artifact scan works; strategy drafting needs signal enrichment layer

### 🔸 Stub (next to build)
- CreditWorker — PII-safe dispute workflow outline
- ContentWorker — brief-to-social + brief-to-newsletter pipeline
- CRMCopilotWorker — GHL workflow audit and suggestion engine
- OpsMonitoringWorker — queue depth + service health checks

### ⬜ Planned
- ClientPortalAssistant — React portal integration, scoped research lookup

---

## Production Safety Notes

- **No AI calls in GrantWorker/OpportunityWorker** — heuristic processing only
- **Additive only** — no worker modifies `research_artifacts` or `research_claims`
- **DRY_RUN=True** in trading engine — stays off until 24h demo monitoring is complete
- **Silent failure** — all workers tolerate missing output tables with a logged warning
- **No client PII** — workers operate only on general research content
- **Mac Mini boundary** — no Oracle VM access, no Windows-side deploys from these modules
