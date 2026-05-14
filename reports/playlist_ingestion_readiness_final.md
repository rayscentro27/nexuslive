# Playlist Ingestion Readiness — Final
Date: 2026-05-13

## Status: READY (gated by PLAYLIST_INGEST_WRITES_ENABLED) ✅

## Worker: lib/playlist_ingest_worker.py

| Feature | Status |
|---------|--------|
| YouTube playlist URL parsing | ✅ Implemented |
| Max videos limit | ✅ PLAYLIST_MAX_VIDEOS_PER_RUN env var (default 10) |
| Duplicate prevention | ✅ Source URL hash dedup before insert |
| transcript_queue writes | ✅ Gated by PLAYLIST_INGEST_WRITES_ENABLED=true |
| Proposed knowledge generation | ✅ Status=proposed, requires admin approval |
| Hermes retrieval | ✅ Queries transcript_queue for playlist items |
| Source trust scoring | ✅ Per-channel trust score via nexus_semantic_concepts |
| Topic clustering | ✅ get_related_concepts() applied per video |

## Safety Gates

- `PLAYLIST_INGEST_WRITES_ENABLED=true` required for any writes (default: false)
- `PLAYLIST_MAX_VIDEOS_PER_RUN` caps videos per run (default 10)
- Never auto-approves knowledge — all records require admin review
- Duplicate detection: no double-insert for same source URL

## Current transcript_queue State

| Status | Count | Domain |
|--------|-------|--------|
| ready | 3 | trading |
| needs_transcript | 10 | trading |

10 real YouTube URLs from NitroTrades channel + related sources are queued and awaiting transcript processing.

## Playlist Registry (from lib/nexus_playlist_registry.py or similar)

Curated playlists ready to ingest:
1. ICT Silver Bullet (trading) — NitroTrades channel
2. Grants Research — CDFI/SBA sources
3. Business Credit — credit-building channels
4. AI Automation Opportunities

## Hermes Playlist Handler

After fix in this pass:
- Queries `transcript_queue` with metadata JSON lookup (not invalid `playlist_id` column)
- Returns: "No playlist-tagged items — X total sources (Y ready, Z awaiting)"
- HTTP 400 bug from invalid column filter: ✅ FIXED

## To Run (Manual Action)

```bash
export PLAYLIST_INGEST_WRITES_ENABLED=true
export PLAYLIST_MAX_VIDEOS_PER_RUN=5
python3 -m lib.playlist_ingest_worker
```

Safe to run tonight — max 5 videos, all writes go to transcript_queue as proposed records.
