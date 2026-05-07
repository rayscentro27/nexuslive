# Funding Engine Spec

## Overview
The Funding Engine is a core commercial component of the Nexus platform, focusing on business funding, credit repair, and financial education. It provides automated scoring, recommendations, and tracking for business capital readiness.

## Core Modules (`funding_engine/`)
1. **Approval Scoring (`approval_scoring.py`)**: Evaluates business and personal credit data to determine funding eligibility.
2. **Business Readiness (`business_readiness_score.py`)**: Scores a business's health and readiness for various capital injections.
3. **Capital Ladder (`capital_ladder.py`)**: Maps out the sequence of funding milestones for a client (e.g., from initial credit repair to large-scale business lines of credit).
4. **Strategy Engine (`strategy_engine.py`)**: Recommends specific financial strategies based on client data and goals.
5. **Relationship Scoring (`relationship_scoring.py`)**: Tracks and scores the depth of relationship with various lenders and partners.

## Readiness Scoring
- Combines business profile strength, credit quality, documentation completeness, and operational consistency.
- Readiness outputs should remain backward compatible with existing score consumers.
- Changes to readiness equations are out of scope unless explicitly requested.

## Relationship Scoring
- Measures lender-alignment quality, communication quality, and prior response outcomes.
- Supports ranking of best-fit capital partners without destructive logic rewrites.

## Capital Ladder
- Defines staged progression from foundational credit stabilization to higher-limit funding options.
- Each stage requires explicit readiness thresholds and risk guardrails.

## Recommendation Engine
- Produces next-best-action recommendations with rationale and urgency.
- Captures outcomes over time for confidence weighting.
- Sparse-data mode must be explicit when evidence quality is low.

## Commission / Referral Structure
- Referral/billing events are tracked as auditable events.
- No billing logic rewrites in this phase.
- Existing payout and event semantics must remain intact.

## Key Features
- **Automated Recommendations**: Generates personalized action plans for clients to improve their funding prospects.
- **Billing & Rewards**: Manages `billing_events.py` and `referral_rewards.py` for monetization and growth.
- **Hermes Integration**: Provides `hermes_brief.py` for generating concise funding summaries for operator review.
- **Lead Intelligence**: Integrated with `ceo_agent/` to track and score incoming leads for the funding funnel.

## Data Sources
- **Client Data**: Business profiles, credit reports, and financial history (managed with PII boundaries).
- **Lender Requirements**: Database of funding criteria from various financial institutions.
- **Market Trends**: Real-time research on business funding availability and rates.

## Monetization Streams
- **Membership Platform**: AI-powered research and strategy reports.
- **Funding Funnel**: Commission and fee-based services for business funding and credit repair.
- **AI Signals**: Premium access to high-probability funding opportunities and strategies.

## Integration Points
- **CRM Portal**: Exposes readiness scores and capital ladders to clients.
- **Supabase**: Stores client progress, scores, and transaction history.
- **CEO Agent**: Feeds revenue and lead metrics to the central tracking system.

## Risk Boundaries (This Phase)
- Do not alter funding/readiness formulas.
- Do not alter production client routes.
- Prefer additive telemetry/spec work over behavioral rewrites.
