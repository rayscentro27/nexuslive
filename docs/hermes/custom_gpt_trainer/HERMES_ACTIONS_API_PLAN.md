# Hermes Actions API Plan

## Purpose

Allow the Nexus CFO Trainer custom GPT to pull live data from Hermes via a simple HTTP API, so Ray does not have to paste failure logs manually.

## Status

**Phase 7B: NOT YET LIVE** — This is a plan for future implementation.
The trainer currently operates from pasted data only.

---

## Planned Endpoints

### GET /hermes/failures

Returns unreviewed failed response examples.

```json
{
  "failures": [
    {
      "id": "...",
      "timestamp": "2026-06-03T10:00:00Z",
      "message": "what was task 1",
      "response": "Based on what I have available...",
      "failure_type": "generic_quality_fallback",
      "reviewed": false
    }
  ]
}
```

**Source:** `docs/reports/training/hermes_failed_response_examples.jsonl`

---

### GET /hermes/training-set

Returns approved training examples.

```json
{
  "examples": [
    {
      "message": "what was task 1",
      "good_response": "PLAIN ANSWER\n\nTask 1 was: ...",
      "bad_response": "Based on what I have available...",
      "failure_type": "generic_quality_fallback"
    }
  ]
}
```

**Source:** `docs/reports/training/hermes_response_training_set.jsonl`

---

### GET /hermes/state

Returns current Hermes operational state summary.

```json
{
  "revenue_readiness_score": 72,
  "approval_queue_count": 3,
  "research_queue_count": 2,
  "last_daily_cycle": "2026-06-03T06:00:00Z",
  "memory_v2_status": "healthy"
}
```

---

### POST /hermes/mark-reviewed

Mark a failure as reviewed.

```json
{
  "failure_id": "...",
  "resolution": "test_added",
  "notes": "Added test_cfo_brain_task_reference.py"
}
```

---

## Authentication

Ray's approval is required before this API is exposed publicly.
- Use a Bearer token stored in Hermes config
- Never expose Supabase credentials
- Rate-limit to 10 req/min
- Localhost only until Ray approves external access

## Safety

This API is read-only except for `mark-reviewed`.
It does not:
- Trigger any Hermes actions
- Write to Supabase old tables
- Send emails or publish content
- Spend money or activate payments

---

## Implementation Checklist (Future Phase)

- [ ] Create `hermes_api_server.py` with FastAPI or Flask
- [ ] Add endpoints above
- [ ] Add Bearer token auth
- [ ] Add rate limiting
- [ ] Write integration tests
- [ ] Get Ray approval before exposing externally
- [ ] Register as Custom GPT Action in OpenAI dashboard

**Requires Ray approval before any external exposure.**
