# NotebookLM Ingestion Connection

## Connected Flow
NotebookLM CLI -> adapter export -> normalized sources -> ingestion jobs -> existing NotebookLM ingest adapter -> `knowledge_items` proposed rows and `transcript_queue` rows -> Hermes internal-first retrieval.

## Routing Verification
- Trading categories route to `trading` destination domain.
- Funding category routes to `funding`.
- Grants category routes to `grants`.
- Business opportunities category routes to `business_opportunities`.

## Current Live Constraint
- CLI auth is missing, so real notebook export currently returns `notebook_not_found`.
- Pipeline logic is connected and test-covered, but live data pull is blocked until `nlm login` is completed.

## Safety
- Proposed review flow preserved.
- No blind overwrite behavior introduced.
- No background Telegram broadcasts introduced.
