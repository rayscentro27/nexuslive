# Email Ingestion Verification

Date: 2026-05-13
Mode: Read-only verification

## Scope

Checked for evidence that an email with subject `trading youtube strategy` and channel `https://www.youtube.com/@nitrotrades` was seen and processed by Hermes/Nexus ingestion.

## Evidence checked

- Local email pipeline state: `.email_pipeline_state.json`
- Workspace/log search for:
  - `trading youtube strategy`
  - `NitroTrades`
  - `nitrotrades`
  - `https://www.youtube.com/@nitrotrades`
- Supabase tables:
  - `transcript_queue`
  - `research_requests`
  - `knowledge_items`

## Results

- Email found: **No evidence found**
- Processed: **No evidence found for this specific message**
- Message ID (target email): **not found**
- Created `transcript_queue` rows: **No** (`count=0`)
- Created `research_request`: **No NitroTrades/youtube-matching rows found**
- Created `knowledge_items`: **No NitroTrades/youtube-matching rows found**

## Hermes mailbox check status

- `.email_pipeline_state.json` contains `processed_message_ids` with count `9`.
- The most recent stored message id was:
  - `<1847486630.707996.1778522629970@mail.yahoo.com>`
- `last_checked_at` and `last_success_at` were `null` in the current state file.

## Errors/warnings

- No targeted NitroTrades/youtube subject trace found in current logs/state/tables.
- Because this pass was read-only, no active mailbox poll (`--once`) was executed.
