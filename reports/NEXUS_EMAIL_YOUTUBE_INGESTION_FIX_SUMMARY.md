# NEXUS Email -> YouTube -> Transcript Queue Ingestion Fix Summary

Date: 2026-05-13

## 1) Root cause

- Mobile subject `trading youtube strategy` did not match legacy tag-based email modes.
- Existing intake path only wrote local dry-run queue and did not write to Supabase `transcript_queue`.
- Channel URL handling was missing as a first-class ingestion bridge.

## 2) Email found/processed status

- Email found: **yes**
- Parsed: **yes**
- Processed: **yes**
- Message id: `<1649585461.489841.1778701622254@mail.yahoo.com>`

## 3) Parser status

- Added simple subject parser mappings for:
  - `trading youtube strategy`
  - `businessopps website ai automation`
  - `grants website arizona business grants`
  - `funding youtube business credit`
  - `credit youtube tradelines`
  - `marketing website funnel`

## 4) transcript_queue insert status

- Insert path implemented and verified against live schema.
- Required non-null `raw_content` field added to payload.
- Duplicate prevention by `source_url` check implemented.
- `transcript_queue` count increased from `0` to `11`.

## 5) Proposed knowledge status

- Proposed knowledge creation enabled for ingested sources.
- 10 new `knowledge_items` rows created with:
  - `status=proposed`
  - domain/title/source_url/source_type
  - quality score heuristic
  - metadata with review-required marker

## 6) Hermes command status

- Supabase-first retrieval updated for:
  - `What new knowledge was ingested?`
  - `What trading videos are ready for review?`
  - `What transcript sources are pending?`
  - `Did Nexus process the NitroTrades email?`
- Responses now resolve from Supabase/state data, not generic fallback.

## 7) Tests run/results

- `python3 scripts/test_knowledge_email_intake_parser.py` -> pass
- `python3 scripts/test_hermes_email_knowledge_intake.py` -> pass
- `python3 scripts/test_email_to_transcript_ingestion.py` -> pass
- `python3 scripts/test_hermes_internal_first.py` -> pass

## 8) Supabase verification

- `transcript_queue`: now populated with YouTube trading rows (`ready` + `needs_transcript`)
- `knowledge_items`: latest proposed rows include newly ingested YouTube records
- `research_requests`: unchanged for this direct ingestion flow

## 9) Git push status

- Pending in working tree at time of report generation (commit/push handled in final step).

## 10) Remaining blockers

- NitroTrades string is not retained in queue row title/source_url because ingestion normalizes to discovered video links.
- Transcript availability depends on public caption availability per video.
