# NEXUS Hermes Retrieval Refinement Summary

Date: 2026-05-13

## 1) Root causes

- Transcript retrieval was constrained to `status=processed` and missed active ingestion rows.
- Confidence weighting undercounted transcript/pending context, pushing unnecessary escalation.
- Retrieval logic was fragmented and too ticket-centric for operational conversational queries.
- NitroTrades/channel recognition depended on URL/title only and lacked robust metadata surfacing.

## 2) Retrieval improvements

- Expanded transcript search to include `title`, `source_url`, `cleaned_content`, and metadata-related context.
- Added helper summaries in `hermes_supabase_first.py`:
  - `summarize_recent_ingestions()`
  - `summarize_transcript_topics()`
  - `summarize_pending_trading_research()`
  - `summarize_recent_approved_knowledge()`

## 3) transcript_queue surfacing status

- Hermes now returns conversational transcript summaries for recent ingestions and pending transcript sources.
- Trading retrieval now includes transcript themes in addition to strategy/ticket context.

## 4) NitroTrades recognition status

- Direct NitroTrades-tagged transcript rows remain dependent on source labeling.
- Hermes now returns state-aware processing status when direct NitroTrades row match is absent.
- Ingestion metadata now includes normalized channel/search tags in row metadata for stronger recognition paths.

## 5) Confidence tuning changes

- `KNOWLEDGE_CONFIDENCE_THRESHOLD` default lowered to 50.
- Confidence weighting updated:
  - approved knowledge strongest
  - transcripts moderate/significant
  - completed research moderate
  - domain hits moderate
  - pending research supportive
- Escalation now requires both low confidence and lack of meaningful internal evidence.

## 6) Synthesis improvements

- Added explicit partial-synthesis response for ICT silver bullet concept queries.
- Trading internal research responses now combine:
  - active strategies
  - pending/completed research
  - transcript themes
  - approved knowledge context

## 7) Escalation reduction results

- `research_request_service.py` now suppresses ticket creation when supportive internal sources exist.
- Router escalation now avoids auto-ticketing when transcript/domain/prior evidence is present.

## 8) Tests/results

- `scripts/test_hermes_retrieval_refinement.py`: PASS
- `scripts/test_hermes_internal_first.py`: PASS
- Live prompt checks completed with conversational retrieval behavior.

## 9) Git push status

- Commit and push completed on `agent-coord-clean` (details in delivery output).

## 10) Remaining blockers

- Some transcript rows are `needs_transcript` due to unavailable public captions.
- Channel-level source naming (e.g., NitroTrades) still depends on available URL/title fields in query path.

## 11) Next refinement recommendations

1. Add explicit `channel_name` top-level DB column if schema changes are approved.
2. Add embedding/semantic retrieval for transcript topic matching.
3. Add ticket creation cooldown by intent signature to further reduce churn.
