# Test Approval Script Report

Date: 2026-05-13
Script: `scripts/approve_knowledge_for_testing.py`

## Purpose

Safely approve selected `knowledge_items` records for testing only.

## Safety controls implemented

- Default mode is dry-run (no writes unless `--apply` is passed).
- Requires either:
  - `--id <knowledge_item_id>`, or
  - `--domain <domain> --limit <number>`
- Rejects mixed targeting (`--id` with `--domain/--limit`).
- Rejects missing/invalid limits and out-of-range quality scores.
- Never performs unlimited approvals.
- Logs approved IDs only and prints before/after summaries.
- Sets values on approval:
  - `status='approved'`
  - `quality_score=85` by default (override via `--quality-score`)
  - `approved_at=now` only if currently null
  - removes leading `[Proposed]` from `title`

## Dry-run validation executed

Command:

`python3 scripts/approve_knowledge_for_testing.py --domain trading --limit 3`

Observed:

- Mode: `DRY-RUN`
- Candidates found: `1`
- Candidate id: `4b0a05a0-f359-4035-a1ad-6f5dff31034c`
- No database changes applied (expected dry-run behavior).

## Usage examples

- Dry-run:
  - `python3 scripts/approve_knowledge_for_testing.py --domain trading --limit 3`
- Apply (batched):
  - `python3 scripts/approve_knowledge_for_testing.py --domain trading --limit 3 --quality-score 85 --apply`
- Apply (single id):
  - `python3 scripts/approve_knowledge_for_testing.py --id <uuid> --quality-score 85 --apply`
