# Recursive Escalation Fix
Date: 2026-05-13

## Problem

Hermes was creating research tickets for its own operational self-queries. When a user asked "What trading research is available internally?" or "What new knowledge was recently approved?", Hermes would:
1. Intercept via `_should_intercept()` (correct)
2. Handle in `_handle_retrieval_query()` (correct)
3. BUT: if `_handle_retrieval_query()` returned an empty-state message and the code fell through, the query could be routed to ticket creation (wrong)

This created recursive escalation loops where Hermes kept generating research tickets to answer its own operational queries.

## Root Cause

`_KNOWLEDGE_TRIGGERS` contained broad patterns like `"what trading research"`, `"what grant"`, `"what opportunities"`, `"recently approved"` — all matching operational self-queries AND legitimate research requests. When `_handle_retrieval_query()` found no data (returning the empty-state string) but the function path fell through, `handle_employee_query()` would sometimes create a ticket.

Additionally, `research_processing_worker.py` would then generate a knowledge_item from the ticket with content `"No vetted Nexus knowledge found for: {topic}"`, which was then incorrectly approved.

## Fixes Applied

### 1. `lib/hermes_supabase_first.py` — Operational query guard

Added `_OPERATIONAL_ONLY_PATTERNS` — a list of exact query patterns that are ONLY handled by retrieval, never eligible for ticket creation:
```python
_OPERATIONAL_ONLY_PATTERNS = [
    "what new knowledge was recently approved",
    "what grant opportunities has nexus researched",
    "what trading research is available internally",
    "what opportunities are nexus validated",
    "what should i focus on today",
    ...
]
```

In `nexus_knowledge_reply()`, after `_handle_retrieval_query()` returns None, the new guard fires:
```python
if _is_operational_only(text):
    return None  # LLM handles it, not the ticket system
```

### 2. `lib/hermes_supabase_first.py` — Empty content suppression

Added `_EMPTY_KNOWLEDGE_MARKERS` and `_content_is_empty()` to detect auto-generated fallback content:
```python
_EMPTY_KNOWLEDGE_MARKERS = (
    "No vetted Nexus knowledge found for:",
    "no vetted nexus knowledge found",
)
```

When `handle_employee_query()` returns `status="found"`, the content is now checked before `_format_found()` is called. If content is an empty marker, the result is treated as `not_found`.

### 3. `lib/research_processing_worker.py` — Block empty knowledge proposals

Added a guard in `_propose_knowledge()` to refuse to create a knowledge_item if the synthesis summary contains the empty-result fallback:
```python
if "No vetted Nexus knowledge found for:" in summary:
    logger.info("_propose_knowledge: suppressed empty-content proposal for ticket %s", ticket["id"])
    return None
```

### 4. `lib/hermes_supabase_first.py` — Playlist handler fix

The playlist handler was querying `transcript_queue` with `playlist_id: "not.is.null"` — but `playlist_id` is not a column in that table (it's stored in the `metadata` JSON). This caused HTTP 400 errors on every playlist query.

Fix: removed the PostgREST filter; now fetches all rows and filters in Python by checking `metadata.playlist_id` or the title string.

## Verification

All 4 recursive tickets cancelled. All 10 spam knowledge_items archived.
Test prompt "What new knowledge was recently approved?" now returns clean retrieval data (only 2 legitimate approved records) without creating a ticket.
