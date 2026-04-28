# OpportunityWorker

Specialized Nexus AI employee that scans research_artifacts for business opportunities, detects recurring niches and service gaps, scores by priority, and surfaces actionable findings via Supabase + Telegram.

## Purpose

Transforms raw business opportunity research (ingested by ResearchWorker from business_opportunities and crm_automation topics) into a ranked, filterable list of vetted opportunities. Also detects repeated niches across sources — a strong signal of real market demand.

## Location

```
~/nexus-ai/workflows/ai_workforce/opportunity_worker/
├── opportunity_worker.js          ← Entry point (direct-run + queue mode)
├── opportunity_normalizer.js      ← Detects type, niche, monetization, urgency
├── opportunity_scoring.js         ← Scores 0-100 using heuristics
└── opportunity_brief_generator.js ← Formats brief + sends Telegram alert
```

## Inputs

| Source | Description |
|--------|-------------|
| `research_artifacts` (Supabase) | Rows with `topic IN ('business_opportunities', 'crm_automation')` |
| `--topic` CLI flag | Optionally restrict to a single topic |
| `--since <days>` CLI flag | Restricts to artifacts created in the last N days |

## Outputs

| Destination | Description |
|-------------|-------------|
| `business_opportunities` (Supabase) | Normalized + scored opportunity records |
| Console | Ranked brief + repeated niche summary |
| Telegram | Alert with top 3 opportunities + niche patterns |

## Normalized Fields

| Field | Source | Example |
|-------|--------|---------|
| `source` | artifact.source | "Codie Sanchez" |
| `title` | artifact.title | "The Psychology of Making Money" |
| `opportunity_type` | Pattern detection | "service_business" |
| `niche` | Keyword matching | "Credit Services" |
| `description` | artifact.summary (≤500 chars) | "..." |
| `evidence_summary` | Top 3 key_points joined | "..." |
| `monetization_hint` | Pattern detection | "Recurring revenue" |
| `urgency` | Keyword signals | "high" / "medium" / "low" |
| `confidence` | From topic classifier | 1.0 |
| `score` | Computed by opportunity_scoring.js | 68 |

## Opportunity Types

| Type | Detection Pattern |
|------|-------------------|
| `saas` | SaaS, MRR, ARR, subscription software |
| `automation_agency` | GoHighLevel, Make.com, n8n, workflow automation |
| `ai_product` | AI tool, LLM app, Claude/GPT-powered |
| `content_creator` | YouTube channel, newsletter, podcast monetization |
| `service_business` | Consulting, coaching, done-for-you, credit consulting |
| `acquisition` | Buy a business, Micro-Acquire, search fund |
| `ecommerce` | Dropshipping, Amazon FBA, Shopify |
| `local_business` | Laundromat, car wash, boring business |
| `other` | Catch-all |

## Scoring Logic (0–100)

| Component | Max Points | Basis |
|-----------|-----------|-------|
| Recurring revenue | 25 | MRR/subscription/retainer keywords |
| Low barrier to entry | 20 | No-code, bootstrap, no inventory signals |
| Proven demand / evidence | 20 | Case studies, data, validated examples |
| Automation / AI leverage | 15 | AI/automation tools mentioned |
| Source authority | 10 | Indie Hackers / Starter Story = highest |
| Novelty / timing | 10 | 2025/2026, emerging, underserved signals |

Minimum score to surface: **35** (configurable with `--min-score`).

## Niche Pattern Detection

OpportunityWorker automatically detects repeated niches across all scored opportunities. When the same niche appears 2+ times across different sources, it's surfaced prominently as a demand signal — independent of individual opportunity scores.

Example output:
```
Recurring niches (signal of demand):
  × 3  CRM Automation
  × 2  Credit Services
```

## Queue Compatibility

```js
// Queue job types: "business_scan", "opportunity_scan"
import { runOpportunityWorker } from "./opportunity_worker/opportunity_worker.js";

const result = await runOpportunityWorker({
  since_days: 7,
  min_score: 40,
  topic: "business_opportunities",  // or null for all
  dry_run: false,
  quiet: true,
});
// result = { opps: [...], brief: {...}, repeated_niches: [...] }
```

## Direct-Run Commands

```bash
cd ~/nexus-ai/workflows/ai_workforce

# Safe dry run — no writes, no Telegram
node opportunity_worker/opportunity_worker.js --dry-run

# Standard run: all opportunity topics, last 30 days
node opportunity_worker/opportunity_worker.js

# CRM automation only, last 14 days
node opportunity_worker/opportunity_worker.js --topic crm_automation --since 14

# Higher threshold, longer window
node opportunity_worker/opportunity_worker.js --since 60 --min-score 50

# All-time scan
node opportunity_worker/opportunity_worker.js --since all

# Quiet mode
node opportunity_worker/opportunity_worker.js --quiet
```

## Supabase Table Setup

Run `docs/business_opportunities.sql` in Supabase SQL editor before first production write:

```sql
-- Creates: business_opportunities table + indexes + view + trigger
-- See: ~/nexus-ai/docs/business_opportunities.sql
```

## Production Safety Notes

- **No AI calls** — heuristic processing only on existing artifacts
- **Additive only** — never modifies research_artifacts or research_claims
- **Silent failure** — if business_opportunities table missing, logs warning and continues
- **No client PII** — operates only on general research content
- **No trading** — purely informational opportunity detection

## Blockers / Prerequisites

1. Run `docs/business_opportunities.sql` in Supabase to create output table
2. Requires research_artifacts rows with `topic IN ('business_opportunities', 'crm_automation')`
3. `SUPABASE_URL` and `SUPABASE_KEY` must be set in `.env`
4. `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` for alerts (optional)
