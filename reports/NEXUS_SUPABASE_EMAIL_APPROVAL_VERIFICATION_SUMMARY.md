# NEXUS Supabase + Email + Approval Verification Summary

Date: 2026-05-13
Mode: Safe verification (read-only default)

## 1) Supabase table counts

- `knowledge_items`: approved `10`, proposed `4`
- `research_requests`: `14` total observed in status breakdown (`needs_review=14`)
- `transcript_queue`: `0`
- `user_opportunities`: `3`
- `provider_health`: provider status snapshot captured (7 providers)
- `analytics_events`: today `0`

## 2) Latest approved/proposed knowledge

- Recent proposed prompts are present (including trading/business/platform/grants prompts).
- Approved trading knowledge includes ICT silver bullet records with `quality_score=85`.

## 3) Research request status

- Current status distribution is concentrated in `needs_review`.
- Latest requests include trading/grants/funding/business prompts and were captured in report.

## 4) transcript_queue status

- Queue currently empty (`0` rows).
- No latest rows available to evaluate ingestion progression.

## 5) NitroTrades email status

- Target subject/content trace not found in local logs/state or Supabase ingestion tables.
- No `transcript_queue` rows for NitroTrades/youtube markers.

## 6) Hermes email check status

- Email pipeline state file exists and includes `processed_message_ids` (count `9`).
- Current state file has `last_checked_at=null` and `last_success_at=null`.

## 7) Test approval script status

- Created `scripts/approve_knowledge_for_testing.py` with guarded dry-run/apply behavior.
- Dry-run test succeeded (`--domain trading --limit 3`), no writes made.

## 8) Hermes reuse status

- Internal routing/retrieval test suites passed:
  - `scripts/test_hermes_internal_first.py`
  - `scripts/test_hermes_knowledge_brain.py`
- Approved ICT silver bullet knowledge exists for internal reuse.

## 9) Blockers

- `supabase status` local health check depends on Docker and failed in this environment.
- No direct evidence of the specific NitroTrades email ingestion in current logs/state/tables.
- Read-only posture prevented mutation-prone live router/ticket assertions.

## 10) Recommended next action

1. Run one controlled mailbox poll (`python3 nexus_email_pipeline.py --once`) during an observation window, then re-check `transcript_queue` and `research_requests` immediately.
2. If NitroTrades content is expected, send/forward a known tagged test email and capture message-id correlation end-to-end.
3. Use `scripts/approve_knowledge_for_testing.py --apply` only for selected rows when explicitly needed for staging validation.
