# Revenue Intelligence Framework

Date: 2026-05-11

## Intelligence Modes (Hermes Extension Concept)
1. Marketing Intelligence
- campaign performance synthesis, message-market fit signals.

2. Content Intelligence
- topic winner detection, hook decay alerts, format rotation suggestions.

3. Opportunity Intelligence
- niche opportunity scoring and queue prioritization.

4. Revenue Strategy Intelligence
- stream mix recommendations by stage and capacity.

5. Trend Intelligence
- early signal collection with confidence tagging.

## Retrieval Priority (unchanged policy)
1. Supabase operational records
2. Nexus internal reports/docs/queues
3. Internal ranked knowledge views
4. External context only when internal evidence is insufficient

## Dashboard Widget Concepts
- content pipeline status (queue stage counts)
- revenue opportunity tracker (ranked opportunities)
- lead generation metrics (source -> conversion)
- onboarding funnel visibility
- affiliate link performance
- business opportunity queue with risk/confidence

## Knowledge Ingestion Enhancements
- stronger category taxonomy (content/revenue/ops/trend)
- source lineage fields (channel, URL, ingest time, confidence)
- normalized YouTube handling (id/channel/topic extraction)
- trend tags + opportunity tags on ingest

## Safety
- `HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false` remains enforced.
- Human review remains required before durable knowledge state transitions.
