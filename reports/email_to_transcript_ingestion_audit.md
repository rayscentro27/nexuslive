# Email to Transcript Queue Ingestion Audit

Date: 2026-05-13

## Pipeline path audited

`goclearonline@gmail.com` (configured as `NEXUS_EMAIL`) 
-> IMAP reader in `nexus_email_pipeline.py`
-> mode detection (`detect_mode`)
-> email parser (`lib/hermes_email_knowledge_intake.py`)
-> subject classifier (`classify_mobile_subject`)
-> ingestion dispatcher (`ingest_email_to_transcript_queue`)
-> Supabase `transcript_queue` + `knowledge_items` writes
-> Hermes retrieval (`lib/hermes_supabase_first.py`)

## Components identified

- Mailbox/IMAP reader: `fetch_unread_nexus_emails` in `nexus_email_pipeline.py`
- Processed message tracking: `.email_pipeline_state.json`
- Subject parser/classifier: `classify_mobile_subject` in `lib/hermes_email_knowledge_intake.py`
- Knowledge email handler: `parse_knowledge_email`
- Ingestion dispatcher: `ingest_email_to_transcript_queue`
- Transcript queue writer: `_supabase_post("transcript_queue", ...)`

## Root cause

1. Plain mobile subject (`trading youtube strategy`) did not match legacy `[NEXUS]/[RESEARCH]` mode tags, so ingestion path was skipped.
2. Existing knowledge intake module was dry-run queue only (local file), not writing to Supabase `transcript_queue`.
3. YouTube extractor focused on direct video URLs; channel URL flows were not bridged to queue inserts.

## Fixes applied

- Added mobile subject parser mappings for six requested subject patterns.
- Added `knowledge_ingestion` mode in `nexus_email_pipeline.py` for URL-bearing, classified subjects.
- Added `process_knowledge_ingestion` to parse and ingest directly into Supabase tables.
- Built transcript queue writer logic against live schema, including required `raw_content` non-null field.
- Added duplicate prevention by `source_url` existence check before insert.
- Added proposed `knowledge_items` creation (status `proposed`, domain, title, source_url, quality score, metadata review flag).
- Added one-shot script for controlled runs: `scripts/process_knowledge_emails_once.py`.

## Safety posture

- `NEXUS_DRY_RUN` and trading safety flags were not modified.
- No secrets printed.
- No email deletion performed.
- Message marked seen/processed only after successful DB writes in apply mode.
