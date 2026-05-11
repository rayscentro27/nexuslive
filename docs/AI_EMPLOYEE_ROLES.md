# Nexus AI Employee Roles

Complete specification for all 10 AI employees in the Nexus AI Workforce.

---

## Role 1 — Research Worker

**ID:** `research_worker`
**Status:** ✅ Implemented
**Audience:** Internal

**Mission:**
Ingest content from all lanes (transcript/manual/browser), extract claims, and write structured artifacts to the Nexus Brain (Supabase).

**Primary Tasks:**
1. YouTube transcript extraction via yt-dlp
2. Manual JSON/text source ingestion
3. Comet browser research (Playwright adapter)
4. Topic classification and claim extraction via OpenClaw
5. Writing research_artifacts, research_claims, memory, graph, clusters

**Input Sources:**
- `sample_sources.json` — registered YouTube channels
- `manual_sources/` folder + `sample_manual_research.json`
- YouTube channels/videos (via yt-dlp)
- Websites (via Comet/Playwright adapter)

**Output Tables:**
`research_artifacts`, `research_claims`, `research`, `research_relationships`, `research_clusters`, `research_briefs`

**Allowed Tools:** yt-dlp, OpenClaw (localhost:18789), Supabase REST API, Telegram
**Blocked Tools:** Broker APIs, client CRM data, live trading systems, Oracle VM

**Implementation:** `workflows/autonomous_research_supernode/research_orchestrator.js`

**Topics Ingested:**
- `grant_research` — Grant opportunities and funding sources
- `business_opportunities` — Service business and SaaS ideas
- `crm_automation` — GoHighLevel, Make.com, workflow automation
- `credit_repair` — FCRA, dispute strategies, credit building
- `trading` — Trading strategies, risk frameworks, market analysis
- `ai_tools` — AI and automation tools for business

---

## Role 2 — Grant Worker

**ID:** `grant_worker`
**Status:** ✅ Implemented
**Audience:** Internal

**Mission:**
Scan grant research artifacts, normalize critical grant fields, score 0–100 using heuristic logic, and surface actionable funding opportunities for small business owners.

**Primary Tasks:**
1. Load `research_artifacts` WHERE `topic = 'grant_research'`
2. Extract program name, funding amount, deadline, geography, eligibility
3. Score 0–100 using heuristic scoring model (no AI calls)
4. Write ranked opportunities to `grant_opportunities`
5. Generate brief and Telegram alert for top grants

**Input Sources:** `research_artifacts` (grant_research topic)
**Output Tables:** `grant_opportunities`, `research_briefs` (optional)

**Scoring Model (max 100):**
| Component | Max | Basis |
|-----------|-----|-------|
| Funding amount | 30 | Normalized dollar value |
| Deadline urgency | 20 | ≤14d=20, ≤30d=18, rolling=12 |
| Geography specificity | 15 | National=10, state=15, international=5 |
| Eligibility clarity | 15 | Matched criteria from key_points |
| Source authority | 10 | Federal/SBA > foundation > blog |
| Confidence bonus | 10 | Artifact classifier confidence × 10 |

**Minimum score to surface:** 30 (configurable with `--min-score`)

**Allowed Tools:** Supabase REST API, Telegram
**Blocked Tools:** yt-dlp, OpenClaw, broker APIs, client PII, Oracle VM

**Implementation:** `workflows/ai_workforce/grant_worker/grant_worker.js`

**Direct Run:**
```bash
node workflows/ai_workforce/grant_worker/grant_worker.js --dry-run
node workflows/ai_workforce/grant_worker/grant_worker.js --since 30 --min-score 40
```

**Prerequisites:** Run `docs/grant_opportunities.sql` in Supabase before first write.

---

## Role 3 — Opportunity Worker

**ID:** `opportunity_worker`
**Status:** ✅ Implemented
**Audience:** Internal

**Mission:**
Scan business opportunity artifacts, detect recurring niches and service gaps, score 0–100, and surface the most actionable monetizable ideas.

**Primary Tasks:**
1. Load `research_artifacts` WHERE `topic IN ('business_opportunities', 'crm_automation')`
2. Detect opportunity type (8 types), niche (16 categories), monetization hint, urgency
3. Score 0–100 using heuristic scoring model (no AI calls)
4. Identify repeated niches across sources as market demand signals
5. Write ranked opportunities to `business_opportunities`
6. Generate brief and Telegram alert with top 3 + niche patterns

**Input Sources:** `research_artifacts` (business_opportunities, crm_automation topics)
**Output Tables:** `business_opportunities`, `research_briefs` (optional)

**Opportunity Types:**
`saas` | `automation_agency` | `ai_product` | `content_creator` | `service_business` | `acquisition` | `ecommerce` | `local_business` | `other`

**Niche Categories (16):**
Real Estate, Credit Services, FinTech, E-Commerce, Healthcare, EdTech, LegalTech, Marketing/Lead Gen, HR/Recruiting, Food & Restaurant, Home Services, Accounting/Finance, CRM Automation, Content/Social Media, AI Automation, SaaS

**Scoring Model (max 100):**
| Component | Max | Basis |
|-----------|-----|-------|
| Recurring revenue potential | 25 | MRR/subscription/retainer keywords |
| Low barrier to entry | 20 | No-code/bootstrap/no-inventory signals |
| Proven demand / evidence | 20 | Case studies, data, validated examples |
| Automation / AI leverage | 15 | AI/automation tools mentioned |
| Source authority | 10 | Indie Hackers/Hormozi = highest |
| Novelty / timing | 10 | 2025/2026, emerging, underserved signals |

**Niche Demand Signal:** When the same niche appears 2+ times across different sources, it's surfaced in the brief as a "recurring niche" — independent of individual scores.

**Minimum score to surface:** 35 (configurable with `--min-score`)

**Allowed Tools:** Supabase REST API, Telegram
**Blocked Tools:** yt-dlp, OpenClaw, broker APIs, client PII, Oracle VM

**Implementation:** `workflows/ai_workforce/opportunity_worker/opportunity_worker.js`

**Direct Run:**
```bash
node workflows/ai_workforce/opportunity_worker/opportunity_worker.js --dry-run
node workflows/ai_workforce/opportunity_worker/opportunity_worker.js --since 14 --topic crm_automation
node workflows/ai_workforce/opportunity_worker/opportunity_worker.js --since 60 --min-score 50
```

**Prerequisites:** Run `docs/business_opportunities.sql` in Supabase before first write.

---

## Role 4 — Credit Worker

**ID:** `credit_worker`
**Status:** 🔸 Stub (pending implementation)
**Audience:** Internal (all outputs reviewed before client exposure)

**Mission:**
Analyze credit repair research artifacts, generate PII-safe dispute workflow templates, and track FCRA / CFPB policy updates.

**Primary Tasks:**
1. Load `research_artifacts` WHERE `topic = 'credit_repair'`
2. Extract dispute strategies, FCRA references, statute citations
3. Generate dispute letter templates (PII-free scaffolds — no client data)
4. Identify CFPB/FTC policy updates and flag high-impact strategies
5. Flag medical debt, authorized user, and rapid rescore opportunities

**Input Sources:** `research_artifacts` (credit_repair topic)
**Output Tables:** `research_briefs`, `credit_dispute_drafts` (future table)

**⚠️ Hard Limits:**
- Zero access to client credit reports, SSNs, DOB, or account numbers
- All dispute templates are generic scaffolds — no client data auto-filled
- All outputs are DRAFT — human advisor reviews before any client use
- Job `credit_dispute_draft` requires human approval gate

**Allowed Tools:** Supabase REST API, Telegram (internal alerts only)
**Blocked Tools:** Raw client credit reports, client SSN/DOB/account numbers, broker APIs, Oracle VM, direct credit bureau API

**Implementation:** `workflows/ai_workforce/credit_worker/` (stub — pending implementation)

**Human Approval Required:** All credit_dispute_draft outputs before client use.

---

## Role 5 — Content Worker

**ID:** `content_worker`
**Status:** 🔸 Stub (pending implementation)
**Audience:** Internal (drafts only — human publishes)

**Mission:**
Generate content briefs, social post drafts, and newsletter outlines from research briefs and opportunity findings. All output is DRAFT — no auto-publishing.

**Primary Tasks:**
1. Read `research_briefs` and `business_opportunities`
2. Generate social post drafts (LinkedIn, Twitter/X format)
3. Generate email newsletter outlines
4. Create content calendars based on research themes
5. Pull top grant and opportunity findings into shareable formats

**Input Sources:** `research_briefs`, `business_opportunities`, `grant_opportunities`
**Output Tables:** `content_drafts` (future table)

**⚠️ Hard Limits:**
- No social media API access (no auto-posting)
- No scheduling or direct platform integration
- All drafts require human review and approval before any publication
- Jobs `content_social_draft` and `content_newsletter_draft` require human approval gate

**Allowed Tools:** Supabase REST API, OpenClaw (for drafting)
**Blocked Tools:** Social media APIs, client PII, broker APIs, Oracle VM

**Implementation:** `workflows/ai_workforce/content_worker/` (stub — pending implementation)

---

## Role 6 — CRM Copilot Worker

**ID:** `crm_copilot_worker`
**Status:** 🔸 Stub (pending implementation)
**Audience:** Internal (staff-facing)

**Mission:**
Analyze CRM automation research and generate actionable GoHighLevel / workflow improvement suggestions for the Nexus CRM stack.

**Primary Tasks:**
1. Load `research_artifacts` WHERE `topic = 'crm_automation'`
2. Identify workflow gaps and automation opportunities
3. Generate GHL pipeline improvement suggestions
4. Draft Zapier/Make.com workflow templates (no auto-execution)
5. Suggest lead response SLA improvements and follow-up sequences

**Input Sources:** `research_artifacts` (crm_automation topic), `business_opportunities`
**Output Tables:** `research_briefs`, `crm_suggestions` (future table)

**⚠️ Hard Limits:**
- No CRM write access without human approval
- No auto-executing workflows
- No access to client contact records or conversation history
- Job `crm_suggestion_generate` requires human approval gate

**Allowed Tools:** Supabase REST API, OpenClaw (for suggestion drafting)
**Blocked Tools:** CRM write access without approval, client PII, auto-executing workflows, broker APIs, Oracle VM

**Implementation:** `workflows/ai_workforce/crm_copilot_worker/` (stub — pending implementation)

---

## Role 7 — Client Portal Assistant

**ID:** `client_portal_assistant`
**Status:** ⬜ Planned
**Audience:** Client-facing (via goclearonline.cc portal)

**Mission:**
Answer client questions using the Nexus research knowledge base. Scoped to approved content only — no raw artifact data exposed to clients.

**Primary Tasks:**
1. Respond to client questions about credit repair, grants, and business opportunities
2. Retrieve approved `research_briefs` relevant to the client's query
3. Generate plain-language explanations from research content
4. Escalate to human staff for sensitive or account-specific questions

**Input Sources (READ ONLY):** `research_briefs`, `grant_opportunities`, `business_opportunities`
**Output Tables:** `portal_responses` (future table — Oracle VM side)

**⚠️ Hard Limits:**
- NONE access to `research_artifacts`, `research_claims`, `research_clusters` — too raw
- No access to client account records, credit reports, or billing data
- All account-specific advice escalated to human staff
- Job `portal_query_respond` requires human approval gate
- Oracle-side integration managed from Windows machine only

**Allowed Tools:** Supabase REST API (read-only, approved tables only)
**Blocked Tools:** Raw research_artifacts, client account records, billing data, broker APIs, Oracle admin actions

**Implementation:** TBD — Oracle-side integration (Windows machine scope)

---

## Role 8 — Trading Research Worker

**ID:** `trading_research_worker`
**Status:** 🔶 Partial
**Audience:** Internal (Ray review only)

**Mission:**
Scan trading research artifacts and generate educational strategy proposals for human review. **NO live trading. NO broker connections. Ever.**

**Primary Tasks:**
1. Load `research_artifacts` WHERE `topic = 'trading'`
2. Extract strategy patterns, risk frameworks, session timing, entry/exit criteria
3. Generate strategy proposal drafts (DRAFT — human reviews before any action)
4. Write proposals to `reviewed_signal_proposals` with status = 'draft'
5. Generate trading research briefs and Telegram alerts

**Input Sources:** `research_artifacts` (trading topic)
**Output Tables:** `reviewed_signal_proposals` (DRAFT only), `research_briefs`

**⚠️ Hard Limits:**
- DRAFT access only to `reviewed_signal_proposals` — never direct WRITE to execution tables
- No OANDA API, no broker execution APIs
- No live signal generation or automatic order placement
- All strategy proposals require human review before RiskComplianceWorker review
- Job `trading_strategy_draft` requires human approval gate

**Allowed Tools:** Supabase REST API, Telegram (internal alerts only)
**Blocked Tools:** OANDA API, broker execution APIs, live signal generation, auto order placement, Oracle VM, client PII

**Implementation:** `workflows/trading_analyst/` (partial) + stub extension at `workflows/ai_workforce/trading_research_worker/`

---

## Role 9 — Risk / Compliance Worker

**ID:** `risk_compliance_worker`
**Status:** ✅ Implemented
**Audience:** Internal

**Mission:**
Review AI-generated proposals and research outputs for compliance issues, flag risks, and enforce Nexus safety rules across all operational domains.

**Primary Tasks:**
1. Review trading strategy proposals against risk rules (drawdown, position size, R:R)
2. Flag compliance issues in credit repair research content
3. Enforce max daily loss ($100), max 3 simultaneous positions, 2:1 R:R minimum
4. Log all risk decisions to `risk_decisions` table
5. Write approvals or rejections to `approval_queue`
6. Send high-risk Telegram alerts

**Input Sources:** `reviewed_signal_proposals`, `research_briefs`, `research_artifacts`
**Output Tables:** `risk_decisions` (WRITE), `approval_queue` (WRITE)

**Risk Rules (Trading):**
- Max daily loss: $100
- Max simultaneous positions: 3
- Minimum risk-to-reward ratio: 2:1
- DRY_RUN=True until 24h demo monitoring complete

**Allowed Tools:** Supabase REST API, Telegram (alerts for high-risk flags)
**Blocked Tools:** Auto-approving trades, broker APIs, client PII, bypassing risk rules, Oracle VM

**Implementation:** `workflows/risk_office/` (implemented)

**Note:** Risk worker approves; human executes. Final execution always requires human action.

---

## Role 10 — Ops / Monitoring Worker

**ID:** `ops_monitoring_worker`
**Status:** 🔸 Stub (pending implementation)
**Audience:** Internal

**Mission:**
Monitor Nexus system health, track queue metrics, detect failures, and send daily operational summaries.

**Primary Tasks:**
1. Check launchd service status (OpenClaw, signal router, dashboard, Telegram bot)
2. Monitor Supabase artifact ingestion rate and row counts
3. Track queue depth across all worker output tables
4. Detect stale data or failed pipeline runs
5. Send daily health report to Telegram

**Input Sources (READ ONLY):** All Supabase tables (counts and timestamps only)
**Output Tables:** None (monitoring only — alerts via Telegram)

**Access Pattern:**
- All table access is `ops_monitoring_worker` level: READ for count queries only
- Never reads full row content, never writes to business tables
- Only destination is Telegram health alert channel

**Allowed Tools:** Supabase REST API (counts/stats queries only), Telegram, launchctl (status queries)
**Blocked Tools:** Supabase writes (except ops logs), broker APIs, client PII, Oracle VM

**Implementation:** `workflows/ai_workforce/ops_monitoring_worker/` (stub — pending implementation)

---

## Approval Gates Summary

| Job | Role | Human Action Required |
|-----|------|-----------------------|
| `credit_dispute_draft` | CreditWorker | Review template before any client use |
| `trading_strategy_draft` | TradingResearchWorker | Review before RiskWorker sees it |
| `content_social_draft` | ContentWorker | Review and publish manually |
| `content_newsletter_draft` | ContentWorker | Review and send manually |
| `crm_suggestion_generate` | CRMCopilotWorker | Review before any GHL changes |
| `portal_query_respond` | ClientPortalAssistant | Review before any client-facing deployment |

All other jobs (research ingestion, grant scanning, opportunity scanning, risk review, ops monitoring) are non-gated and can run on schedule.

---

## Implementation Status Summary

| Role | Status | Module |
|------|--------|--------|
| ResearchWorker | ✅ Implemented | `autonomous_research_supernode/` |
| GrantWorker | ✅ Implemented | `ai_workforce/grant_worker/` |
| OpportunityWorker | ✅ Implemented | `ai_workforce/opportunity_worker/` |
| RiskComplianceWorker | ✅ Implemented | `risk_office/` |
| TradingResearchWorker | 🔶 Partial | `trading_analyst/` + stub |
| CreditWorker | 🔸 Stub | `ai_workforce/credit_worker/` |
| ContentWorker | 🔸 Stub | `ai_workforce/content_worker/` |
| CRMCopilotWorker | 🔸 Stub | `ai_workforce/crm_copilot_worker/` |
| OpsMonitoringWorker | 🔸 Stub | `ai_workforce/ops_monitoring_worker/` |
| ClientPortalAssistant | ⬜ Planned | Oracle-side (Windows scope) |
