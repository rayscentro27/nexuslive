# YouTube Ingestion Connection

Date: 2026-05-15

Connected Hermes YouTube channel/playlist commands to existing ingestion flow.

Supported ingestion intents:
- channel URL ingestion (`ingest this channel ...`)
- playlist URL ingestion (`ingest this playlist ...`)

Operational behavior:
- max latest 30 videos
- dedup-aware insertion path
- transcript queue writes through existing intake service
- proposed knowledge item path remains existing worker pipeline
- source tracking preserved through transcript queue metadata

Telegram policy remains manual response only; no auto status broadcasts.
