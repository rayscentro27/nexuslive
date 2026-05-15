# Research Escalation Loop — Audit and Status
Date: 2026-05-15

## Status: NO ACTIVE ESCALATION LOOPS ✅

## Audit Findings

### research_request_service.py — Query Cooldown (already in place)

`_find_recent_ticket_by_normalized_query()` checks for any ticket with the same normalized query created within `RESEARCH_QUERY_COOLDOWN_MINUTES` (default: 30 minutes).

```python
RECENT_QUERY_COOLDOWN_MINUTES = int(os.getenv("RESEARCH_QUERY_COOLDOWN_MINUTES", "30") or "30")
cutoff_iso = (datetime.now(timezone.utc) - timedelta(minutes=max(1, RECENT_QUERY_COOLDOWN_MINUTES))).isoformat()
```

If a matching recent ticket is found, status is `"duplicate"` — no new ticket written. Hermes shows the user the existing ticket instead.

### research_processing_worker.py — Error Handling (no re-queue)

Failed tickets transition to `"rejected"` status, not back to `"submitted"`. `_fetch_open_tickets()` only fetches `status in (submitted, queued)` — rejected tickets are never retried.

```python
def _reject_ticket(ticket_id: str, reason: str) -> bool:
    ...  # sets status = "rejected"

except Exception as exc:
    _reject_ticket(ticket_id, f"Processing error: {exc}")
```

### hermes_supabase_first.py — Operational Query Firewall (already in place)

`_OPERATIONAL_ONLY_PATTERNS` prevents operational self-queries from falling through to ticket creation. These never generate research tickets regardless of how many times they are asked:
- "what should i focus on today"
- "ingestion status"
- "what grant opportunities has nexus researched"
- etc.

### No Telegram Calls in Workers

Neither `research_processing_worker.py` nor `research_request_service.py` make any Telegram API calls. The summary dict returned by `run_processing_loop()` is passed to the CEO worker for digest formatting — it does not auto-send.

## Configurable Cooldown

To increase same-query recreation cooldown:
```bash
export RESEARCH_QUERY_COOLDOWN_MINUTES=120  # 2 hours
```
