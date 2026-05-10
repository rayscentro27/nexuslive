# Knowledge Email Parser Audit

Date: 2026-05-10

## Current Parser Flow
- Entry parser module: `lib/hermes_email_knowledge_intake.py`.
- Core parse path:
  - `parse_knowledge_email(sender, subject, body, message_id)`
  - `build_proposed_records(parsed, dry_run=True)`
  - `ingest_knowledge_email_dry_run(...)` writes queue + markdown report.
- Queue path: `reports/knowledge_intake/proposed_records_queue.json`.

## Metadata Extraction Location
- Sender/subject/message_id/timestamp extraction occurs in:
  - `parse_knowledge_email(...)`
  - `parse_gmail_hydrated_message(...)` (new hydrated Gmail adapter path)

## URL Extraction Location
- Plain-text URL extraction: `_urls(text)`.
- HTML anchor extraction: `_urls_from_html(html)`.
- HTML body fallback stripping: `_strip_html(html)`.

## Hydrated Message Support
- Added `parse_gmail_hydrated_message(message)` to parse Gmail-style hydrated payload/headers/parts.
- Handles snippet fallback when bodies are sparse.

## Root Cause of Prior Validation Gap
- Queue rows in previous samples lacked sender/subject/link metadata because ingestion records were minimal and likely ingested through sparse input fields.
- URL extraction was text-centric and could miss anchor-only links in hydrated HTML parts.
