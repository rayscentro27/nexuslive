# Autonomous Opportunity Engine

## Purpose
The Autonomous Opportunity Engine turns Nexus Brain research outputs into structured, prioritized opportunities without changing infrastructure, schema, or control-plane ownership.

It reads from:
- `research_artifacts`
- `research_claims`
- `research_clusters`
- `research_hypotheses`
- `coverage_gaps`

It produces:
- prioritized opportunities with owner routing
- concise brief payloads
- actionable next-step suggestions

## Safety Boundaries
- Research-only processing.
- No live trading, no broker execution.
- No Oracle control-plane changes.
- No client PII extraction.
- Additive files only.

## Implementation Location
- `workflows/ai_workforce/autonomous_opportunity_engine/autonomous_opportunity_engine.js`
- `workflows/ai_workforce/autonomous_opportunity_engine/opportunity_detector.js`
- `workflows/ai_workforce/autonomous_opportunity_engine/opportunity_normalizer.js`
- `workflows/ai_workforce/autonomous_opportunity_engine/opportunity_ranker.js`
- `workflows/ai_workforce/autonomous_opportunity_engine/opportunity_action_generator.js`
- `workflows/ai_workforce/autonomous_opportunity_engine/opportunity_brief_generator.js`

## Opportunity Types
- `grant_opportunity`
- `business_opportunity`
- `service_gap`
- `automation_idea`
- `saas_idea`
- `product_improvement`
- `niche_alert`

Normalized output fields:
- `id`
- `source`
- `title`
- `opportunity_type`
- `niche`
- `description`
- `evidence_summary`
- `monetization_hint`
- `urgency`
- `confidence`
- `score`
- `recommended_owner`
- `trace_id`
- `created_at`

## Owner Routing Model
- `grant_opportunity` -> `GrantWorker`
- `business_opportunity` -> `OpportunityWorker`
- `service_gap` -> `CRM/Product`
- `automation_idea` -> `Ops/Automation`
- `saas_idea` -> `OpportunityWorker`
- `product_improvement` -> `CRM/Product`
- `niche_alert` -> `OpportunityWorker`

## Queue + Direct-Run Compatibility
Queue-compatible job types:
- `opportunity_scan`
- `grant_opportunity_scan`
- `service_gap_scan`
- `automation_idea_scan`
- `opportunity_brief_generation`

Direct-run commands:
```bash
cd ~/nexus-ai/workflows/ai_workforce
node autonomous_opportunity_engine/autonomous_opportunity_engine.js --dry-run --since 30 --limit 20
node autonomous_opportunity_engine/autonomous_opportunity_engine.js --job-type grant_opportunity_scan --dry-run
node autonomous_opportunity_engine/autonomous_opportunity_engine.js --job-type service_gap_scan --min-score 40 --dry-run
```

NPM script:
```bash
cd ~/nexus-ai/workflows/ai_workforce
npm run autonomous-opportunity -- --dry-run --since 21
```

Programmatic queue-style usage:
```js
import { runOpportunityEngineJob } from "./autonomous_opportunity_engine/autonomous_opportunity_engine.js";

await runOpportunityEngineJob({
  job_type: "opportunity_scan",
  since_days: 14,
  min_score: 45,
  dry_run: true,
});
```

## Persistence Behavior
Default behavior is conservative:
- reads from research tables
- computes opportunities
- writes a compact brief to `research_briefs` (unless `--no-brief`)
- does **not** write business/grant opportunity rows unless `--persist`

`--persist` writes:
- grant-type opportunities -> `grant_opportunities`
- business/automation/service-gap style opportunities -> `business_opportunities` (mapped to compatible enum types)

## Schema Gap (Documented, Not Applied)
Current schemas do not provide a dedicated canonical table for all opportunity types (`service_gap`, `niche_alert`, `product_improvement` as first-class records).

Low-risk future addition (optional):
- `autonomous_opportunities` table with full type coverage
- keep existing `grant_opportunities` and `business_opportunities` unchanged

No schema changes were auto-applied in this phase.
