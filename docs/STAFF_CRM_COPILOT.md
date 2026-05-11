# Staff CRM Copilot

## Overview

The Staff CRM Copilot analyzes CRM automation research artifacts and generates GoHighLevel / workflow improvement suggestions for internal staff review. All outputs are **DRAFT only** — no CRM changes are ever made automatically.

## Purpose

Help Nexus staff:
- Identify workflow gaps in the current CRM setup
- Surface GoHighLevel pipeline improvement ideas from research
- Draft Zapier/Make.com automation templates for human review
- Stay current on CRM automation best practices from ingested content

## Knowledge-First Policy

Requests are resolved in this priority order:

```
1. Classify query intent (local, zero-cost)
2. Query research_artifacts (crm_automation topic) from Supabase
3. Query business_opportunities for cross-reference
4. Generate heuristic-based suggestions (no AI calls)
5. [Future] OpenClaw for richer suggestion drafting
6. Return DRAFT suggestions for human review
```

## Approved Data Access

| Table | Access | Notes |
|-------|--------|-------|
| `research_artifacts` | READ | crm_automation + business_opportunities topics |
| `research_claims` | READ | CRM-related claims |
| `research_briefs` | READ + WRITE | Can write CRM briefs |
| `business_opportunities` | READ | Cross-reference for opportunity ideas |
| `crm_suggestions` | WRITE (future) | Draft suggestions output table |

**Denied tables:**

| Table | Reason |
|-------|--------|
| `reviewed_signal_proposals` | Trading domain — not CRM |
| `risk_decisions` | Risk management only |
| `approval_queue` | Risk/compliance only |
| Client CRM records | PII — never accessible to this worker |

## Request Flow

```
Staff member submits query
        │
        ▼
copilot_request_router.js (audience="staff")
        │  ← Staff authentication (Oracle VM handled auth)
        │  ← No tenant isolation needed (staff = internal)
        │
        ▼
Staff query resolver
        │
        ├── 1. Classify intent (crm_insight, grant_summary, etc.)
        ├── 2. Load research_artifacts WHERE topic = crm_automation
        ├── 3. Detect CRM tools mentioned (GoHighLevel, Make.com, etc.)
        ├── 4. Detect CRM categories (Follow-up Sequences, Pipeline Automation, etc.)
        ├── 5. Generate draft suggestions (heuristic — no AI calls)
        │
        ▼
Draft suggestions returned for human review
        │
        ▼
Staff reviews + implements (manually in GHL)
```

## Suggestion Categories

| Category | Detection Patterns |
|---------|-------------------|
| Lead Generation / Nurturing | lead gen, lead nurture |
| Follow-Up Sequences | follow-up, follow up sequence |
| Pipeline Automation | pipeline stage, pipeline automation |
| Appointment Booking | appointment booking, scheduling |
| Client Onboarding | onboarding flow, onboarding automation |
| Email Campaigns | email campaign, email sequence |
| SMS Automation | SMS automation, SMS follow |
| API / Webhook Integration | webhook, API integration |
| Review Requests | review request, review automation |
| Reporting & Analytics | reporting dashboard, analytics |

## CRM Platform Detection

The worker identifies which platforms are mentioned in research:
- GoHighLevel (GHL)
- HubSpot
- Make.com / Integromat
- Zapier
- n8n
- ActiveCampaign
- Salesforce
- Pipedrive

Suggestions are tagged with the relevant platform.

## Hard Limits

- **No direct CRM writes** — all suggestions are drafts for human implementation
- **No auto-execution** of workflows, Zapier steps, or Make.com scenarios
- **No client contact records** — worker operates on research data only, not live CRM data
- **No PII access** — only sees aggregated research content
- `crm_suggestion_generate` job type requires human approval gate in dispatcher

## Direct Run Commands

```bash
cd ~/nexus-ai/workflows/ai_workforce

# Safe dry run — no Telegram, output only
node crm_copilot_worker/crm_copilot_worker.js --dry-run

# Standard run — last 30 days of crm_automation research
node crm_copilot_worker/crm_copilot_worker.js

# Broader window
node crm_copilot_worker/crm_copilot_worker.js --since 60

# Quiet mode
node crm_copilot_worker/crm_copilot_worker.js --quiet

# Via dispatcher
node workforce_dispatcher.js --role crm_copilot_worker --job crm_workflow_scan --dry-run
```

## Via Dispatcher

```bash
# Requires human approval gate to be bypassed (after human sign-off)
node workforce_dispatcher.js \
  --role crm_copilot_worker \
  --job crm_suggestion_generate \
  --skip-approval \
  --since 14
```

## Prerequisites

- `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- `research_artifacts` rows with `topic = 'crm_automation'` (run research pipeline with crm_automation sources)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` for alerts (optional)

## Future Work

- **crm_suggestions table** — create Supabase table for draft suggestion storage
- **OpenClaw integration** — use `/v1/chat/completions` for richer suggestion drafting
- **GHL template library** — build a curated library of proven automation templates
- **Slack/portal integration** — surface suggestions in staff dashboard (Oracle VM scope)
