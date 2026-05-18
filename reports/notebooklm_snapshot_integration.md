# NotebookLM Snapshot Integration

## Updated
- `lib/central_operational_snapshot.py` now includes `notebooklm` block.

## Fields Added
- notebooks_total
- enabled_count
- last_sync_at
- pending_sync_count
- latest_sync_status
- latest_error
- proposed_knowledge_count
- queue_rows_created
- categories_covered

## Notes
- Snapshot values are derived from:
  - `notebooklm/notebook_registry.json`
  - `reports/knowledge_intake/notebooklm_intake_queue.json`
  - existing `knowledge_items` status counts
- `latest_error` currently returns `None` (reserved field for follow-up runtime error persistence).
