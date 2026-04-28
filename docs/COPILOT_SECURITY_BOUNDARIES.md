# Copilot Security Boundaries

Security model, tenant protections, and data access rules for the Nexus AI copilot system.

---

## Copilot Roles Overview

| Role | Module | Audience | Status |
|------|--------|----------|--------|
| Client Portal Assistant | `client_portal_assistant.js` | Client-facing (portal) | Implemented |
| Staff CRM Copilot | `crm_copilot_worker.js` | Internal staff | Implemented |

---

## Fundamental Security Principles

### 1. Mac Mini Never Serves Clients Directly

The Mac Mini AI node does **not** have a public HTTP endpoint. All client-facing requests flow through:

```
Client → Oracle VM (nexus-oracle-api) → [auth + tenant validation] → Mac Mini logic
```

The Mac Mini exports JavaScript modules (`resolvePortalQuery`, `routeCopilotRequest`). The Oracle VM calls these after completing its own security checks.

### 2. Authentication is Oracle's Responsibility

The Oracle VM (`api.goclearonline.cc`) is responsible for:
- JWT validation
- Session management
- Tenant ID extraction from auth context
- Rate limiting per user/tenant
- Abuse prevention

Mac Mini modules receive `tenant_id` as a pre-validated parameter — they trust the Oracle layer to have verified it.

### 3. Tenant Isolation

For portal requests:
- `tenant_id` is required and must be passed in every `resolvePortalQuery()` call
- Mac Mini does not join tables by tenant (it has no tenant-scoped data)
- The tenant boundary is enforced at the Oracle VM layer
- Knowledge base (research_briefs, opportunities, grants) is shared across tenants — no tenant-specific data is returned

For staff requests:
- Staff users are internal — no tenant isolation needed
- Staff ID is logged for audit trail purposes only

### 4. No Cross-Tenant Data Leakage

Nexus research data is general-purpose (not tenant-specific), so cross-tenant leakage is not possible for knowledge queries.

For any future client-specific data (credit report summaries, dispute drafts, etc.):
- These **must not** be stored in shared tables
- These **must** be stored in tenant-scoped tables with RLS (Row Level Security) on Supabase
- Mac Mini copilots are **blocked from accessing these tables** in `copilot_permissions.js`

---

## Data Access Matrix

### Client Portal Assistant

| Data Type | Access | Method |
|-----------|--------|--------|
| Research briefs | ✅ READ | Supabase, filtered |
| Grant opportunities | ✅ READ | Supabase, score >= 30, status = new |
| Business opportunities | ✅ READ | Supabase, score >= 35, status = new |
| Raw research artifacts | ❌ DENIED | Hard-blocked in code |
| Client credit reports | ❌ DENIED | Not in Mac Mini scope |
| Client account records | ❌ DENIED | Oracle VM only |
| Billing records | ❌ DENIED | Not in Mac Mini scope |
| Trading proposals | ❌ DENIED | Internal only |
| Other tenant data | ❌ DENIED | Tenant isolation |

### Staff CRM Copilot

| Data Type | Access | Method |
|-----------|--------|--------|
| Research artifacts (crm_automation) | ✅ READ | Supabase, topic filtered |
| Research claims | ✅ READ | Supabase |
| Research briefs | ✅ READ + WRITE | Supabase |
| Business opportunities | ✅ READ | Supabase |
| Grant opportunities | ✅ READ | Supabase |
| Client contact records (GHL/CRM) | ❌ DENIED | Not in Mac Mini scope |
| Trading proposals | ❌ DENIED | Internal only |
| Risk decisions | ❌ DENIED | Risk/compliance only |

---

## Permanently Blocked Actions (All Copilots)

These actions are permanently blocked in `copilot_permissions.js` and cannot be unlocked:

| Blocked Action | Reason |
|----------------|--------|
| `access_client_credit_reports` | PII — requires specialized secure workflow |
| `access_client_account_records` | PII — Oracle VM scope only |
| `access_billing_data` | Payment data — not in Mac Mini scope |
| `mutate_crm_workflows_directly` | Human approval required for all CRM changes |
| `execute_automation_scripts` | No auto-execution of any automation |
| `post_to_social_media` | Requires human review and approval |
| `send_emails_to_clients` | Oracle VM scope only |
| `access_broker_api` | No broker connections anywhere |
| `access_oracle_vm_directly` | Mac Mini cannot SSH/call Oracle VM |
| `cross_tenant_data_read` | Tenant isolation enforced at Oracle VM layer |
| `read_raw_research_artifacts_as_portal` | Too raw for client-facing responses |

---

## Human Approval Gates

These jobs require explicit human approval before the dispatcher will invoke them:

| Job | Copilot | Human Action Required |
|-----|---------|----------------------|
| `portal_query_respond` | Client Portal Assistant | Review before deploying Oracle endpoint |
| `crm_suggestion_generate` | Staff CRM Copilot | Review before any GHL changes |

All suggestion outputs are `status: "draft"` and include `requires_human_review: true` in the response payload.

---

## Escalation Protocol

When the portal assistant detects an account-specific or sensitive query, it **does not attempt to answer** — it returns an escalation response immediately:

```
Escalation triggers:
  - "my account", "my credit report", "my score"
  - "billing", "refund", "cancel my"
  - "dispute my", "my case", "my file"
  - "login issue"

Escalation response:
  "This question requires personalized attention. A team member will follow up."
```

The Oracle VM backend should record escalations and trigger a staff notification.

---

## Knowledge-First Resolution Policy

Before any AI model is called, copilots must attempt to resolve queries from structured data:

```
Priority 1: Structured Supabase data
            (research_briefs, grant_opportunities, business_opportunities)

Priority 2: [Future] ai_cache lookup
            (cached AI responses to identical/similar queries)

Priority 3: [Future] AI model (OpenClaw via /v1/chat/completions)
            Only if priorities 1 and 2 return empty results
            AND the query does not trigger escalation

Never:      Raw client data passed to AI model
Never:      Unauthenticated queries routed to knowledge base
Never:      AI model output sent directly to client without Oracle review
```

---

## Safe Empty State Handling

When no knowledge is found, copilots return safe placeholder messages:

| Scenario | Portal Response | Staff Response |
|----------|-----------------|----------------|
| No grants found | "Updating database — contact our team" | "Run GrantWorker —since 30" |
| No opportunities | "Research team adding content" | "Run OpportunityWorker" |
| No CRM insights | — | "Run research pipeline topic=crm_automation" |
| System error | Generic "something went wrong" | Logged + Telegram alert |

**Never expose:** stack traces, Supabase error messages, environment variables, or internal table names in responses to clients.

---

## Audit Logging

All copilot requests should be logged with:
- `tenant_id` (from Oracle auth)
- `staff_id` (for staff requests)
- `intent` (classified locally)
- `response_type` (knowledge / escalation / empty / error)
- `tables_queried` (for security review)
- `escalated` (boolean)
- `timestamp`

Oracle VM is responsible for persisting audit logs. Mac Mini returns `intent`, `response_type`, and `escalated` in every response for Oracle to log.

---

## Request Validation Rules

| Check | Where | On Failure |
|-------|-------|------------|
| JWT validity | Oracle VM | 401 Unauthorized |
| Tenant ID present | Oracle VM | 403 Forbidden |
| Rate limit | Oracle VM | 429 Too Many Requests |
| Query non-empty string | Mac Mini (`copilot_request_router.js`) | 400 Bad Request |
| Audience valid ("staff"/"portal") | Mac Mini | 400 Bad Request |
| Tenant ID present for portal | Mac Mini | Error thrown |
| Table in approved list | Mac Mini (`copilot_permissions.js`) | Error thrown |
| Action not blocked | Mac Mini | Error thrown |

---

## Production Safety Checklist

Before enabling portal queries in production:

- [ ] Oracle VM `/api/copilot/portal-query` endpoint built and deployed (Windows machine)
- [ ] JWT validation enabled on Oracle endpoint
- [ ] Tenant ID extraction working from session
- [ ] Rate limiting configured (suggested: 20 queries/minute per tenant)
- [ ] Escalation notifications wired to staff (Telegram or email)
- [ ] `portal_responses` table created in Supabase for audit logging
- [ ] RLS enabled on any future client-specific tables
- [ ] `research_briefs`, `grant_opportunities`, `business_opportunities` populated
- [ ] Dry-run test: `node client_portal_assistant/client_portal_assistant.js --dry-run`
