# NotebookLM CLI Adapter

## Implemented File
- `lib/notebooklm_cli_adapter.py`

## Functions Added
- `list_notebooks()`
- `get_notebook_sources(notebook_id)`
- `export_notebook(notebook_id)`
- `sync_notebook(notebook_id)`
- `normalize_notebook_export(raw)`
- `build_ingestion_jobs(normalized)`
- `dry_run_sync(notebook_id)`
- `apply_sync(notebook_id)`

## Safety Controls
- Dry-run default behavior in sync paths.
- Timeout-bounded CLI subprocess calls.
- Credential-keyword redaction before returning CLI output.
- Safe per-notebook item caps (`max_items_per_sync` bounded).
- Dedup at normalization step using URL/title hash.
- Graceful failure when CLI unavailable or unauthenticated.

## Operational Notes
- Adapter uses existing ingestion bridge (`lib/notebooklm_ingest_adapter.py`) for Supabase-proposed record writes.
- No auto-approval logic introduced.
