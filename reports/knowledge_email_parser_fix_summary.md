# Knowledge Email Parser Fix Summary

Date: 2026-05-10

## Files Changed
- `lib/hermes_email_knowledge_intake.py`
- `scripts/test_knowledge_email_intake_parser.py`

## Fixes
- Sender parsing improved (`Name <email>` and raw email detection).
- Subject/message-id extraction supports hydrated Gmail headers.
- HTML email body stripping fallback added.
- HTML anchor URL extraction added.
- Category detection improved (explicit `CATEGORY:` first, then subject/body keywords).
- Proposed record metadata enriched with sender/subject/received_at/links_count.

## Test Results
- `python3 scripts/test_knowledge_email_intake_parser.py` passed.

## Real Queue Validation Status
- Historical queue rows may still lack metadata.
- Fresh hydrated message path now supports full metadata extraction when used by ingress connector.

## Rollback
- `git checkout -- lib/hermes_email_knowledge_intake.py scripts/test_knowledge_email_intake_parser.py`
