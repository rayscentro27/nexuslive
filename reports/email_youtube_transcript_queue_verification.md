# Email + YouTube + Transcript Queue Verification

Date: 2026-05-13

## NitroTrades email detection

- Subject searched: `trading youtube strategy`
- URL searched: `https://www.youtube.com/@nitrotrades`
- Email found: **yes**
- Parsed: **yes**
- Processed in dry-run: **yes**
- Processed in apply: **yes**
- Message id: `<1649585461.489841.1778701622254@mail.yahoo.com>`
- Skip reason (initial apply attempt): schema mismatch (`transcript_queue.raw_content` required); fixed.

## One-shot runner output

Dry-run command:

`python3 scripts/process_knowledge_emails_once.py --subject-filter "trading youtube strategy" --dry-run`

Observed:

- candidates: `1`
- processed: `1`
- expanded_urls: `10`
- transcript_rows_prepared: `10`
- knowledge_rows_prepared: `10`

Apply command:

`python3 scripts/process_knowledge_emails_once.py --subject-filter "trading youtube strategy" --apply`

Observed after fix:

- processed: `1`
- marked_seen: `1`
- transcript_rows_inserted: `10`
- knowledge_rows_inserted: `10`

## Supabase verification (post-apply)

- `transcript_queue` count: `11` (from prior `0` baseline)
- latest rows: include multiple `youtube` trading rows with statuses `ready` and `needs_transcript`
- `knowledge_items` proposed rows: include 10 new trading YouTube proposed records
- `research_requests`: no new rows required for this ingestion path

## Target marker verification

- NitroTrades direct string in `transcript_queue` rows: **not present** (rows are normalized to discovered video URLs)
- YouTube source presence: **present**
- Bridge objective (email -> transcript_queue) status: **fixed and verified**
