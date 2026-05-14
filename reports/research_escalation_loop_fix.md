# Research Escalation Loop Fix

## Problem

- Repeated low-confidence queries could produce repeated escalations close together.
- Existing dedup relied on broad topic matching and open-ticket checks, which can miss near-identical repeat attempts.

## Fix

- Updated `lib/research_request_service.py` to add normalized-query cooldown suppression:
  - Added recent-query lookup by `normalized_query` + department + open statuses
  - Applied cooldown window via `RESEARCH_QUERY_COOLDOWN_MINUTES` (default 30)
  - If recent ticket exists, return `status=duplicate` immediately (no recreate)

## Effect

- Same-query recreation is blocked during cooldown.
- Reduces repeated escalation retries and repeated "needs_review/researching" notification pressure.
