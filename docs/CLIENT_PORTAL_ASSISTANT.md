# Client Portal Assistant

## Overview

The Client Portal Assistant answers client questions on the `goclearonline.cc` portal using the Nexus research knowledge base. It is scoped to approved, curated content only — no raw research data is ever exposed to clients.

## Scope Boundary

**Mac Mini scope (this machine):**
- Research knowledge lookup from approved Supabase tables
- Response generation using heuristic matching
- Query intent classification
- Escalation detection

**Oracle VM scope (Windows machine — NOT this machine):**
- HTTP endpoint: `POST /api/copilot/portal-query`
- Authentication and tenant validation
- Rate limiting and abuse protection
- `portal_responses` table writes
- Delivery of approved responses to the React frontend

## Knowledge-First Policy

Requests are resolved in this priority order:

```
1. Classify query intent (local, zero-cost)
2. Detect escalation requirement (local)
3. Query approved Supabase tables (READ only)
4. Return structured knowledge response
5. [Future] Check ai_cache before calling AI model
6. [Future] AI model (OpenClaw) as last resort only
```

AI model calls are not yet wired in — the assistant returns structured knowledge from the database first.

## Approved Data Access

| Table | Access | Notes |
|-------|--------|-------|
| `research_briefs` | READ | Curated summaries only |
| `grant_opportunities` | READ | New, scored grants only |
| `business_opportunities` | READ | New, scored opportunities only |

**Denied tables (hard-blocked, enforced in code):**

| Table | Reason |
|-------|--------|
| `research_artifacts` | Too raw — contains unprocessed ingestion data |
| `research_claims` | Too detailed — internal extraction data |
| `research_clusters` | Internal categorization — not client-facing |
| `research_relationships` | Internal graph data |
| `reviewed_signal_proposals` | Trading data — not client-facing |
| `risk_decisions` | Internal risk management |
| `approval_queue` | Internal workflow |

## Request Flow

```
Client (goclearonline.cc portal)
        │
        ▼
Oracle VM — POST /api/copilot/portal-query
        │  ← Auth check (JWT / session)
        │  ← Tenant validation (ensure tenant_id matches session)
        │  ← Rate limiting (prevent abuse)
        │
        ▼
Mac Mini — resolvePortalQuery({ query, tenant_id })
        │
        ├── 1. Sanitize query (max 500 chars)
        ├── 2. Classify intent (grant_lookup, business_ideas, credit_guidance, etc.)
        ├── 3. Check escalation patterns (account-specific, billing, credit reports)
        │        └── If escalation → return escalation response (no knowledge lookup)
        ├── 4. Query approved table(s) by intent
        ├── 5. Build safe response (no raw data leakage)
        │
        ▼
Oracle VM — Review draft response
        │  ← Log to portal_responses (optional)
        │
        ▼
Client sees: Safe, curated summary or escalation message
```

## Intent Classification

| Intent | Trigger Keywords | Knowledge Source |
|--------|-----------------|-----------------|
| `grant_lookup` | grant, funding, SBA, apply for | `grant_opportunities` |
| `business_ideas` | opportunity, side hustle, make money | `business_opportunities` |
| `credit_guidance` | credit, dispute, score, repair | `research_briefs` |
| `crm_guidance` | CRM, workflow, automation | `research_briefs` |
| `general_research` | explain, learn, what is | `research_briefs` |

## Escalation Detection

The following query patterns always escalate to human staff — no AI response is generated:

- `my account`, `my credit report`, `my score`, `my payment`
- `billing`, `refund`, `cancel my`
- `dispute my`, `my case`, `my file`
- `login issue`

Escalation response: "This question relates to your personal account. A Nexus team member will follow up with you directly."

## Response Types

| Type | When | Client Sees |
|------|------|-------------|
| `knowledge` | Knowledge found | Safe bullet-point summary + "Contact us for personalized guidance" |
| `escalation` | Account-specific query | Human follow-up message |
| `empty` | No knowledge found | "Updating database" message + contact prompt |
| `error` | System failure | Generic error message (no internals exposed) |

## Hard Limits

- No cross-tenant data access (tenant_id validated by Oracle backend)
- No client account records, credit reports, or billing data
- No raw `research_artifacts` content exposed
- Account-specific advice always escalated to human staff
- `portal_query_respond` job type requires human approval gate in dispatcher

## Direct Run (Test Mode)

```bash
cd ~/nexus-ai/workflows/ai_workforce

# Test intent classification and knowledge lookup (dry run)
node client_portal_assistant/client_portal_assistant.js --dry-run

# Test with a specific query
node client_portal_assistant/client_portal_assistant.js "What grants are available for small businesses?"

# Test escalation detection
node client_portal_assistant/client_portal_assistant.js "How do I dispute my credit report?"
```

## Implementation Location

```
workflows/ai_workforce/client_portal_assistant/
└── client_portal_assistant.js    ← Mac Mini logic (knowledge lookup + response)

Oracle VM (Windows machine, nexus-oracle-api):
└── src/routes/copilot/           ← HTTP endpoint, auth, tenant validation
    └── portal-query.ts
```

## Prerequisites

- `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- `research_briefs` table populated (run research pipeline)
- `grant_opportunities` table created (run `docs/grant_opportunities.sql`)
- `business_opportunities` table created (run `docs/business_opportunities.sql`)
- Oracle VM endpoint and auth (Windows machine scope)
