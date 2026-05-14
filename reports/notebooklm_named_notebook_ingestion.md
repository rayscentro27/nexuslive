# NotebookLM Named Notebook Ingestion

## Implemented

- Added named notebook-to-domain mapping in `lib/notebooklm_ingest_adapter.py`:
  - Nexus Grants -> grants
  - Nexus Trading -> trading
  - Nexus Funding -> funding
  - Nexus Credit -> credit
  - Nexus Business Opportunities -> business_opportunities
  - Nexus Marketing -> marketing
  - Nexus Operations -> operations

- Added one-shot ingestion commands:
  - `python3 -m lib.notebooklm_ingest_adapter --notebook "Nexus Grants" --dry-run`
  - `python3 -m lib.notebooklm_ingest_adapter --notebook "Nexus Grants" --apply`

- Added all-configured ingestion commands:
  - `python3 -m lib.notebooklm_ingest_adapter --all-configured --dry-run`
  - `python3 -m lib.notebooklm_ingest_adapter --all-configured --apply`

- Added NotebookLM capability diagnostics command:
  - `python3 -m lib.notebooklm_ingest_adapter --capability-check`

## Proposed knowledge payload behavior

- Stores proposed records with:
  - `source_type=notebooklm`
  - `status=proposed`
  - mapped `domain`
  - metadata with `source_name`, `source_urls`, `insights`, `review_required=true`
  - calculated `quality_score`

- Duplicate prevention:
  - deterministic `dedup_key`
  - dry-run queue duplicate check
  - apply-mode duplicate check against existing proposed knowledge metadata dedup keys

- Optional transcript queue support:
  - creates `transcript_queue` rows for YouTube-like source URLs when applying
  - marks transcript rows as `needs_transcript`

## Current run observation

- Named ingest commands execute safely.
- In this environment, notebooks were not listed because NotebookLM profile auth is not active.
