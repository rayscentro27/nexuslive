# NotebookLM Knowledge Dry-Run

Date: 2026-05-10

## Queue Source
- `reports/knowledge_intake/notebooklm_intake_queue.json`

## Adapter
- `lib/notebooklm_ingest_adapter.py`
- Produces proposed records with:
  - `source_type`
  - `notebook_name`
  - `topic`
  - `summary`
  - `key_takeaways`
  - `action_items`
  - `category`
  - `confidence`
  - `dry_run=true`

## Dry-Run Result
- Queue loaded and summarized successfully.
- No writes to Supabase.
- No Knowledge Brain auto-store activation.

## Hermes Query Support
- “What NotebookLM research is ready?”
- “Summarize NotebookLM intake queue”

Both route internal-first to dry-run queue summary.
