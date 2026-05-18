# Nexus AI Workforce Infrastructure

**Created:** 2026-05-18
**Status:** Foundation complete — Phase 1 implemented

---

## Architecture Overview

Nexus AI Workforce Infrastructure extends the existing `ai_task_queue` / Hermes orchestration
system with a structured planning layer, agent/skill/CLI registries, risk gating,
and a Workforce Command Center admin UI.

**Core principle:** Prefer existing Nexus/Supabase flows before introducing external tools.
CLI-first for operational tasks. Human approval required for risky actions.

---

## System Components

### 1. Nexus Agent Dispatcher (`lib/agent_dispatcher/`)

The central routing engine. Takes a natural language prompt from Ray/admin,
classifies it, assesses risk, builds a subtask plan, and assigns agents/skills/CLIs.

**Files:**
- `lib/agent_dispatcher/__init__.py` — package exports
- `lib/agent_dispatcher/registry.py` — loads agent_capabilities, nexus_skills, nexus_cli_tools
- `lib/agent_dispatcher/planner.py` — task classification, clarification detection, subtask planning
- `lib/agent_dispatcher/router.py` — agent/provider selection with health-aware fallbacks
- `lib/agent_dispatcher/risk.py` — risk level assessment with hard block patterns

**Status:** ✅ Foundation complete

---

### 2. Hermes Workforce Router

Hermes is the primary orchestrator. All tasks from Telegram/admin flow through Hermes,
which uses the Dispatcher to route appropriately.

**Existing foundation:**
- `lib/hermes_supabase_first.py` — Supabase-first knowledge routing
- `lib/hermes_internal_first.py` — Internal operational memory routing
- `lib/ai_task_dispatch.py` — Task queue operations (create, list, update)

**What's new:**
- Hermes now uses `hermes_response_patterns` table for conversational replies
- Greeting/status patterns return operationally-grounded responses
- `lib/hermes_response_patterns.py` module with Supabase + embedded fallback

**Status:** ✅ Personality upgrade complete, 12/12 response quality tests passing

---

### 3. Nexus Skill Library (`nexus_skills` table)

10 initial skills seeded:
| Skill | Category | Risk |
|-------|----------|------|
| funding_readiness_v1 | funding | low |
| credit_dispute_generator_v1 | credit | medium |
| grant_research_v1 | grants | low |
| business_launch_site_v1 | launch | medium |
| seo_cluster_builder_v1 | seo | low |
| ceo_digest_v1 | ops | low |
| client_followup_draft_v1 | comms | medium |
| worker_health_audit_v1 | ops | low |
| utility_python_job_v1 | ops | medium |
| qa_review_v1 | qa | low |

All require_approval=true for medium/high risk. Prompt templates stored in DB.

---

### 4. Nexus CLI Layer (`nexus_cli_tools` table + `bin/nexus`)

8 initial CLI tools registered:
| CLI Key | Command | Risk |
|---------|---------|------|
| nexus_health | nexus health | low |
| nexus_report | nexus report | low |
| nexus_worker | nexus worker | low (approval for writes) |
| nexus_funding | nexus funding | medium |
| nexus_comms | nexus comms | low |
| nexus_launch | nexus launch | medium |
| nexus_grants | nexus grants | low |
| nexus_seo | nexus seo | low |

**Routing rule:** Use CLI first for operational/monitoring tasks before LLM invocation.

---

### 5. Nexus Model Router (`lib/agent_dispatcher/router.py`)

Selects providers by:
- Task type and risk level
- Provider health (from `provider_health` table)
- Cost tier preference for low-risk tasks
- Fallback list when primary is degraded

**Cost tier priority (low-risk tasks):**
1. ollama (free local)
2. groq (free tier)
3. openrouter / deepseek
4. claude_subscription / anthropic (reserved for coding/architecture)

---

### 6. Nexus Workforce Command Center (Admin UI)

Route: **Admin → 🤖 AI Team → Workforce Command** tab (within AdminAIWorkforce)
Or: New admin route `workforce-command`

Sections:
1. Dispatch Inbox (received, needs_clarification, awaiting_approval, blocked)
2. Active Runs (parent tasks, subtasks, agent assignments, status)
3. Resource Registry (agents, skills, CLIs, providers)
4. Approval Queue (approve/reject with risk reason)
5. Completed Summaries

**Status:** ✅ NexusWorkforceCommand.tsx created

---

### 7. Pyrunner Utility Automation Layer

Python Runner worker (`pyrunner_worker` in agent_capabilities) handles:
- Scheduled ingestion jobs
- Report generation
- Data processing pipelines

Safety: requires_approval=true for medium-risk tasks. --dry-run default.

---

### 8. Embedded Intelligence Layer

The existing `lib/hermes_knowledge_brain.py`, `lib/strategy_intelligence.py`,
and `lib/opportunity_intelligence.py` form the embedded intelligence layer.

**New additions:**
- `hermes_response_patterns` table — conversation personality memory in Supabase
- Response pattern matching in `hermes_internal_first.py`

---

## Safety Rules (Hard-Coded)

| Rule | Status |
|------|--------|
| NEXUS_DRY_RUN=true | Always |
| LIVE_TRADING=false | Always |
| No auto-send external messages | Enforced by hermes_gate.py |
| No production deploy without approval | Enforced by risk.py |
| No expose secrets | Enforced by hermes_gate.py redact() |
| No mass approve knowledge blindly | Review required by default |

---

## Supabase Schema (New Tables)

1. `hermes_response_patterns` — conversational personality templates
2. `agent_capabilities` — agent registry with task types + risk levels
3. `nexus_skills` — skill library with prompt templates
4. `nexus_cli_tools` — CLI command registry
5. `agent_dispatch_tasks` — high-level dispatch requests
6. `agent_dispatch_subtasks` — planned subtasks with agent assignments
7. `agent_dispatch_events` — execution event log
8. `human_approval_requests` — pending human approvals

**Existing (not duplicated):**
- `ai_task_queue`, `ai_task_workers`, `ai_task_results`, `ai_task_activity_log`
- `provider_health`

---

## API Endpoints (Planned)

Backend routes to add (Phase 2):
- `GET /api/admin/agent-dispatch/resources`
- `POST /api/admin/agent-dispatch/tasks`
- `GET /api/admin/agent-dispatch/tasks`
- `POST /api/admin/agent-dispatch/tasks/:id/plan`
- `GET /api/admin/agent-dispatch/approvals`
- `POST /api/admin/agent-dispatch/approvals/:id/approve`

---

## Next Steps

1. Apply Supabase migrations to live DB
2. Wire `agent_dispatch_tasks` creation to Telegram command handler
3. Add Fastify/Nexus API endpoints for dispatch tasks
4. Implement `nexus health --json` CLI in `bin/nexus`
5. Connect Workforce Command Center UI to live Supabase tables
6. Test full dispatch flow: Telegram → Dispatcher → Subtasks → Approval → Completion
