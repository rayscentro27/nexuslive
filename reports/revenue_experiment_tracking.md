# Revenue Experiment Tracking

Date: 2026-05-15

## Tracking model

`revenue_engine/revenue_experiment_tracker.py` defines a foundation experiment record with:

- Opportunity identity: `opportunity_name`, `category`, `confidence`
- Recommendation bundle: affiliate, lead magnet, newsletter topic, mini tool, landing page experiment
- Execution constraints:
  - `paid_ads_autopublish=false`
  - `auto_spend_enabled=false`
  - `auto_payment_processing=false`
  - `real_payment_flows_enabled=false`
- Metrics fields:
  - `impressions`
  - `clicks`
  - `leads`
  - `conversions`
  - `estimated_revenue`
  - `confirmed_revenue`

## Recommendation logic

Rule set source: `revenue_engine/revenue_foundation_config.json`

Current baseline rules:

1. Funding-path
   - Keywords: funding/loan/capital/SBA/CDFI
   - Bundle: Bluevine + Funding Readiness Checklist + Funding newsletter topic + Funding Readiness Score + Funding CTA

2. Credit-growth
   - Keywords: credit/utilization/tradeline/score
   - Bundle: SmartCredit + Vendor Starter Pack + Credit newsletter topic + Credit Utilization Optimizer + Credit CTA

3. Automation-build
   - Keywords: automation/workflow/AI tool/operations
   - Bundle: Zapier + Automation Starter Guide + Automation newsletter topic + AI Idea Generator + Automation CTA

Fallback bundle is provided when no rule matches.

## Admin visibility

Read-only stub is exposed through central snapshot payload under `revenue_engine` and includes:

- Newsletter readiness and queue depth
- Affiliate stack totals
- Lead magnet count
- Mini-tool roadmap count
- Digital product outline count
- Waitlist field structure
- Experiment rule count

## What this phase does not do

- Does not run ads
- Does not route payments
- Does not spend money
- Does not assign real affiliate IDs automatically
- Does not claim revenue events without tracked conversions

## Test coverage

- `scripts/test_revenue_engine_foundation.py` validates experiment constraints remain:
  - `paid_ads_autopublish=false`
  - `auto_spend_enabled=false`
  - `auto_payment_processing=false`
  - `real_payment_flows_enabled=false`
