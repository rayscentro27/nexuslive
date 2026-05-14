# Telegram Summary Removal Tests

## Tests executed

- `python3 scripts/test_telegram_summary_removal.py`
  - conversational reply allowed
  - explicit digest request allowed
  - research/ingestion/scheduler/ticket/worker summaries denied
  - missing event_type denied

- `python3 scripts/test_hermes_internal_first.py`
  - normal conversational routing remains active

- `python3 scripts/test_research_request_spam_guard.py`
  - recent normalized-query duplicate suppression works

- `python3 scripts/test_email_to_transcript_ingestion.py`
  - ingestion regression and duplicate prevention remain intact

## Result

- All listed tests passed in this pass.
