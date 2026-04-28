# Nexus AI Employee Hierarchy

Canonical hierarchy for the Nexus AI workforce, showing who controls what, how work flows, and where approvals happen.

This document reflects both:
- the intended organizational structure
- the current live operating pattern in the Nexus stack

---

## 1. Executive / Control Layer

These components act as the command and coordination layer for the workforce.

### `nexus-orchestrator`

**Role:** Central executive coordinator  
**Responsibility:** Receives events, creates workflows, routes jobs, and tracks worker state.

**Owns:**
- `system_events`
- `job_queue`
- `orchestrator_workflow_runs`
- `worker_heartbeats`

**Reports to:** Human operator  
**Directs:** Research and specialist workers

### `coordination_worker`

**Role:** Secondary coordination / system state support  
**Responsibility:** Supports orchestration state and worker coordination.

**Reports to:** `nexus-orchestrator`

---

## 2. Intelligence / Ingestion Layer

These workers gather and structure raw knowledge for the rest of the workforce.

### `research_worker`

**Role:** Primary intelligence collector  
**Responsibility:** Ingests YouTube transcripts, manual sources, and browser research; extracts claims and writes structured knowledge into Supabase.

**Primary outputs:**
- `research_artifacts`
- `research_claims`
- `research`
- `research_relationships`
- `research_clusters`
- `research_briefs`

**Reports to:** `nexus-orchestrator`  
**Feeds:** All specialist workers

---

## 3. Specialist Worker Layer

These workers convert research into domain-specific outputs.

### `grant_worker`

**Role:** Funding opportunity analyst  
**Responsibility:** Scores `grant_research` artifacts and writes ranked grant opportunities.

**Primary outputs:**
- `grant_opportunities`
- optional `research_briefs`

**Reports to:** `nexus-orchestrator`  
**Consumes:** `research_artifacts`

### `opportunity_worker`

**Role:** Business opportunity analyst  
**Responsibility:** Scores `business_opportunities` and `crm_automation` artifacts and writes ranked monetizable ideas.

**Primary outputs:**
- `business_opportunities`
- optional `research_briefs`

**Reports to:** `nexus-orchestrator`  
**Consumes:** `research_artifacts`

### `credit_worker`

**Role:** Credit strategy analyst  
**Responsibility:** Produces draft dispute workflows and policy tracking from `credit_repair` research.

**Primary outputs:**
- future `credit_dispute_drafts`
- optional `research_briefs`

**Reports to:** `nexus-orchestrator`  
**Consumes:** `research_artifacts`  
**Requires approval:** Yes

### `crm_copilot_worker`

**Role:** CRM systems analyst  
**Responsibility:** Produces CRM/process improvement suggestions from automation research.

**Primary outputs:**
- future `crm_suggestions`
- optional `research_briefs`

**Reports to:** `nexus-orchestrator`  
**Consumes:** `research_artifacts`, `business_opportunities`  
**Requires approval:** Yes

### `content_worker`

**Role:** Content production analyst  
**Responsibility:** Produces draft content assets from briefs and opportunity outputs.

**Primary outputs:**
- future `content_drafts`

**Reports to:** `nexus-orchestrator`  
**Consumes:** `research_briefs`, `business_opportunities`, `grant_opportunities`  
**Requires approval:** Yes

### `trading_research_worker`

**Role:** Trading strategy research analyst  
**Responsibility:** Produces educational strategy drafts from trading artifacts.

**Primary outputs:**
- `reviewed_signal_proposals` with `status = draft`
- optional `research_briefs`

**Reports to:** `nexus-orchestrator`  
**Consumes:** `research_artifacts`  
**Requires approval:** Yes

---

## 4. Risk / Compliance Layer

This layer sits above specialist outputs when safety, approval, or compliance review is required.

### `risk_compliance_worker`

**Role:** Internal control and risk authority  
**Responsibility:** Reviews AI-generated proposals and enforces Nexus safety rules, especially around trading and sensitive domains.

**Primary outputs:**
- `risk_decisions`
- `approval_queue`

**Reports to:** Human operator  
**Reviews:** Specialist-worker outputs  
**Authority:** Can approve, reject, or escalate

### Human Approval Gates

Human review remains above the AI compliance layer for sensitive actions.

**Human-gated jobs:**
- `credit_dispute_draft`
- `trading_strategy_draft`
- `content_social_draft`
- `content_newsletter_draft`
- `crm_suggestion_generate`
- `portal_query_respond`

---

## 5. Delivery / Interface Layer

This layer exposes approved or internal outputs to humans and client-facing systems.

### `client_portal_assistant`

**Role:** Client-facing response layer  
**Responsibility:** Answers client questions using approved tables only.

**Readable inputs:**
- `research_briefs`
- `grant_opportunities`
- `business_opportunities`

**Reports to:** Human operator / portal governance  
**Blocked from:** Raw artifact tables

### Internal Delivery Channels

These are not “employees,” but they are part of the delivery path.

**Includes:**
- Telegram alerts
- Dashboard
- internal operational logs

---

## 6. Operations / Platform Layer

These components keep the workforce alive, observable, and connected.

### `ops_monitoring_worker`

**Role:** Internal operations monitor  
**Responsibility:** Tracks service health, queue depth, stale data, and operational failures.

**Reports to:** Human operator  
**Reads:** system metrics and counts only

### `ops_control_worker`

**Role:** Internal control-plane executor  
**Responsibility:** Tracks desired worker state, validates control requests, and acts as the safe execution layer for future start/stop/schedule changes.

**Current runtime role:**
- reads `worker_control_plane`
- validates `worker_control_actions`
- supports read-only ops diagnosis
- does not directly mutate live services yet

**Reports to:** Human operator / ops governance  
**Supports:** Hermes and the wider workforce control plane

### `openclaw_gateway`

**Role:** Shared AI gateway / model runtime  
**Responsibility:** Exposes the local LLM API surface, handles model routing, manages provider authentication, and acts as the shared inference layer for Nexus services.

**Current runtime role:**
- serves `/v1/chat/completions`
- routes Nexus inference traffic to configured model providers
- supports Hermes and other internal AI callers

**Reports to:** Ops / platform governance  
**Supports:** Hermes, research flows, and any worker or service that calls the local AI gateway

### `hermes`

**Role:** Internal AI reviewer / decision-support agent  
**Responsibility:** Performs higher-judgment analysis and review tasks, especially around signals, trading review, and internal decision support.

**Current runtime role:**
- consumes OpenClaw for inference
- acts as a specialist reasoning layer rather than a standalone workforce employee
- supports review-oriented workflows before human action

**Reports to:** Human operator and governance/risk flows  
**Depends on:** `openclaw_gateway`

### Supporting Platform Services

These are additional system-level runtime dependencies for the workforce.

**Includes:**
- Ollama
- Signal router
- Telegram bot
- Dashboard
- Scheduler
- mac-mini worker

These services do not “report” like employees, but they support the workforce at the infrastructure level.

---

## 7. Command Chain Summary

In plain English, the command flow is:

1. Human operator defines priorities and approves sensitive actions.
2. `nexus-orchestrator` routes events and dispatches work.
3. `research_worker` generates structured intelligence.
4. Specialist workers convert intelligence into business, grant, CRM, trading, credit, or content outputs.
5. Hermes provides internal AI review and decision support where higher-judgment analysis is needed.
6. `risk_compliance_worker` and human gates review sensitive outputs.
7. Delivery layers expose approved outputs to internal users or clients.
8. Ops/platform services, including OpenClaw, keep the system alive and observable.

---

## 8. Live Operating Hierarchy

As of the current live system, the hierarchy that is actually active is:

### Live and active
- `nexus-orchestrator`
- `research_worker`
- `grant_worker`
- `opportunity_worker`
- `ops_control_worker`
- `openclaw_gateway`
- `hermes`
- Ollama
- Signal router
- Telegram bot
- Dashboard
- Scheduler

### Implemented but not consistently active as dedicated workers
- `risk_compliance_worker`
- `trading_research_worker`
- `ops_monitoring_worker`

### Stubbed or planned
- `credit_worker`
- `content_worker`
- `crm_copilot_worker`
- `ops_monitoring_worker`
- `client_portal_assistant`

---

## 9. Reporting Structure At A Glance

### Human operator
- `nexus-orchestrator`
- `risk_compliance_worker`
- client-facing deployment decisions

### `nexus-orchestrator`
- `research_worker`
- `grant_worker`
- `opportunity_worker`
- `credit_worker`
- `content_worker`
- `crm_copilot_worker`
- `trading_research_worker`
- `ops_monitoring_worker`

### `research_worker`
- feeds all specialist workers

### `risk_compliance_worker`
- reviews sensitive downstream outputs before human action

### `client_portal_assistant`
- consumes approved outputs only

---

## 10. Recommended Future Formalization

To make the hierarchy even clearer over time, Nexus should eventually define:

- a canonical dispatcher for all worker jobs
- explicit worker dependencies in one registry
- approval routing rules by job type
- ownership of every Supabase table by layer
- a live org/status dashboard showing:
  - active
  - idle
  - scheduled
  - stubbed
