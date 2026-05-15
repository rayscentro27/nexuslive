# Telegram Channel Ingestion

- Added Telegram-ingestion handling in `lib/hermes_supabase_first.py` for:
  - `ingest this channel <youtube-channel-url>`
  - `what channels are processing?`
  - `what videos were ingested?`
  - existing `what knowledge is pending review?` remains supported
- Channel ingestion now expands up to 30 videos max per channel in `lib/hermes_email_knowledge_intake.py`.
- Dedupe behavior preserved through existing `transcript_queue` source URL checks.

## Policy safety
- Conversational reply only; no auto-summary fanout added.
- Ingestion reply confirms preparation/inserts while explicitly noting no Telegram summary broadcast.
