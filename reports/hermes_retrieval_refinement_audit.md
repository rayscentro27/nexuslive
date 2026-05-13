# Hermes Retrieval Refinement Audit

Date: 2026-05-13

## Scope audited

- `lib/hermes_supabase_first.py`
- `lib/ai_employee_knowledge_router.py`
- `lib/research_request_service.py`
- `lib/hermes_internal_first.py`
- `transcript_queue` retrieval and confidence logic

## Root causes found

1. Transcript surfacing underweighted and too narrow
   - `ai_employee_knowledge_router.py` queried `transcript_queue` with `status=processed` only.
   - Active rows were `ready` / `needs_transcript`, so many relevant records were ignored.
   - Query did not include `source_url`, metadata context, or broader status set.

2. Over-escalation bias
   - Escalation depended on strict threshold with low transcript contribution.
   - Ticket creation path in `research_request_service.py` did not suppress escalation when supportive internal sources existed.

3. Ticket-centric retrieval responses
   - `hermes_supabase_first.py` had retrieval branches but limited synthesis between transcripts, approved knowledge, and pending research.

4. NitroTrades/source recognition inconsistency
   - Ingested rows were normalized to video URLs, so channel-name references were not reliably visible in row title/source_url.
   - Channel/source metadata needed stronger normalization for recognition.

5. Confidence threshold too strict for partial operational answers
   - Default threshold favored escalation over partial conversational synthesis.

## Decision flow before refinement

- Query -> router confidence score -> escalation if confidence < threshold.
- Transcript presence added only a small score and was often absent due to restrictive status filter.

## Refinement objective

- Favor informed partial synthesis from internal records.
- Escalate only when meaningful internal data is truly absent.
- Surface transcript evidence and pending-review context conversationally.
