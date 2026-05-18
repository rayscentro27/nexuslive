# Notebook Registry

## Implemented
- Created `notebooklm/notebook_registry.json`.
- Added 11 category-aligned entries:
  - forex_trading
  - options_trading
  - crypto_trading
  - stock_trading
  - business_funding
  - business_credit
  - grants
  - ai_automation
  - business_opportunities
  - marketing
  - operations

## Tracked Fields
- notebook_id
- notebook_name
- category
- description
- source_type
- sync_status
- last_sync_at
- last_ingested_at
- confidence
- enabled
- max_items_per_sync
- destination_domain

## Status
- Registry loads through `scripts/nexus_notebooklm_ops.py registry`.
- `status` currently reports 11 enabled notebooks.
- Sync status remains idle until CLI auth is completed.
