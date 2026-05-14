# Email + Playlist Ingestion Visibility
Date: 2026-05-13

## Problem
No admin visibility into what Nexus has processed from email or YouTube sources. No way to answer: "Did the latest email get processed? What domain was it? Did it fail?"

## Solution: IngestionStatusPanel (NEW)
Admin → AI Team → Ingestion tab now shows a live view of transcript_queue.

### Status Chips
| Status | Color | Label |
|--------|-------|-------|
| processed | Green #16a34a | Processed ✅ |
| needs_transcript | Purple #7c3aed | Needs Transcript 🎤 |
| needs_review | Amber #d97706 | Needs Review 👁️ |
| pending | Gray | Pending ⏳ |
| failed | Red #dc2626 | Failed ❌ |
| duplicate | Light gray | Duplicate 🔁 |

### Features
- Summary bar: Total / Processed / Pending / Failed counts
- Domain filter dropdown (auto-built from live data)
- Status filter dropdown
- Per-item: domain emoji, title, source icon (YouTube/Email/Generic), trust score, time ago
- Auto-refresh 60s with last-sync timestamp
- Empty state: hints to run hermes_email_knowledge_intake.py or playlist_ingest_worker.py

### Source Icons
- YouTube URL → red YouTube icon
- email/mailto channel → Mail icon
- Other → Inbox icon

## AdminAIWorkforce.tsx Change
Added "Ingestion" tab between "Tickets" and "Agents":
```
['Office', 'Tickets', 'Ingestion', 'Agents', 'Activity', 'Events']
```

## TypeScript Notes
- `domains` and `statuses` arrays typed as `string[]` (not `unknown[]`) via explicit cast from Set
- `STATUS_CONFIG[s]?.label` uses optional chaining for unknown status strings

## Commit
- nexuslive main → `39c75f6`
- IngestionStatusPanel.tsx: NEW
- AdminAIWorkforce.tsx: +1 tab route
