# NotebookLM Ingestion Pipeline

## Current Flow (Implemented)
NotebookLM CLI -> notebook/source fetch -> dedup key generation -> dry-run queue -> optional Supabase proposed records.

## Required Target Flow
NotebookLM -> export extraction -> semantic classification -> dedup -> structured intelligence extraction -> Supabase storage -> Hall of Fame evaluation -> roadmap intelligence -> Hermes retrieval.

## Completion Status by Stage
- Sync queue: Partial (file queue exists; no durable job state machine).
- Ingestion jobs: Partial (CLI-driven, not scheduled orchestration).
- Source dedup: Implemented (hash key on notebook/source/summary).
- Semantic extraction: Partial (lightweight extraction; no deep semantic pipeline).
- Category routing: Partial (static notebook map + default operations fallback).
- Confidence scoring: Partial (heuristic quality score only).
- Metadata tracking: Partial (record-level metadata exists; notebook-level sync ledger missing).

## Operational Refinements
1. Introduce job states: `queued`, `running`, `needs_review`, `approved`, `rejected`, `synced`.
2. Persist per-run metrics: notebooks scanned, records proposed, dedup dropped, confidence distribution.
3. Add contradiction flags when new notebook themes conflict with accepted strategy lessons.
4. Add bounded retry policy (max retries, backoff, dead-letter queue).

## Integration Hooks
- Hall of Fame inputs: promoted strategies/opportunities only after approval.
- Roadmap intelligence: push recurring themes as roadmap suggestions with confidence tags.
- Hermes: add notebook recency and confidence signals in answer templates.

## Safety
- Keep approval-required path for all NotebookLM-derived records.
- No autonomous external posting from this pipeline.
