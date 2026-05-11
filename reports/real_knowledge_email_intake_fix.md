# Real Knowledge Email Intake Fix

Date: 2026-05-10

## Before
- Validation showed rows with:
  - sender: `None`
  - subject: `None`
  - links: `0`
  - category: `funding`

## After (Parser/Extraction Upgrades)
- Added sender normalization and email extraction (`Name <email>` safe parse).
- Added Gmail hydrated message parser support (`payload.headers`, `parts`, base64 decode).
- Added HTML body stripping fallback.
- Added HTML anchor URL extraction (href links).
- Added category detection priority order (explicit CATEGORY, subject/body keywords, fallback).
- Added richer record metadata on proposed rows (sender, sender_email, subject, received_at, links_count).

## Root Cause
- Existing queue rows likely came from sparse-message ingestion path where sender/subject/body fields were absent or not hydrated.
- URL extraction previously focused on plain text and missed anchor-only links in hydrated HTML payloads.

## Files Changed
- `lib/hermes_email_knowledge_intake.py`
- `scripts/test_knowledge_email_intake_parser.py`

## Remaining Limitations
- Current queue snapshot still contains older rows lacking metadata (historical data quality issue).
- Full real-email confirmation depends on source mailbox ingestion connector invoking hydrated parser path.

## Rollback
- Revert parser/test changes:
  - `git checkout -- lib/hermes_email_knowledge_intake.py scripts/test_knowledge_email_intake_parser.py`
