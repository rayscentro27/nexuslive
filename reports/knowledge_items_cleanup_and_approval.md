# Knowledge Items Cleanup and Approval Pass

Date: 2026-05-13
Mode: CLI/script-driven, safe cleanup

## 1) Script existence + capability check

Script found: `scripts/approve_knowledge_for_testing.py`

Confirmed capabilities:

- Default dry-run behavior (`--apply` required for writes)
- Supports targeted approval by `--id <uuid>`
- Supports bounded domain approvals `--domain <domain> --limit <n>`
- Prevents unlimited approvals
- Removes leading `[Proposed]` prefix from titles in approval flow
- Safely updates `quality_score` (bounded 0-100)

Enhancements added in this pass:

- `--archive-low-quality` cleanup mode
- hard requirement: `--max-quality-score 50` + `--apply`
- cleanup changes status to `rejected`/`archived` (non-destructive)
- `--clean-approved-prefix` mode for already-approved rows with noisy `[Proposed]` prefix

## 2) Read-only audit before apply

Pre-cleanup:

- approved count: `10`
- proposed count: `15`
- low-quality approved count (`<=50`): `5`
- titles containing `[Proposed]`: `20` rows
- duplicate prompt-like titles: none detected
- latest 20 rows: captured during audit command output

## 3) Dry-run first (exact targeted rows)

Dry-run commands executed before apply:

1. `python3 scripts/approve_knowledge_for_testing.py --clean-approved-prefix --quality-score 75`
   - candidates: `5` approved rows

2. `python3 scripts/approve_knowledge_for_testing.py --id a0a19677-4474-482c-960c-754608bc1ce6 --quality-score 80`
   - candidate: `1` proposed row (useful transcript-backed record)

3. Read-only archive candidate listing (`status=proposed`, `quality_score<=50`)
   - candidates: `14` rows

## 4) Apply actions (after exact-row dry-run)

Applied commands:

1. `python3 scripts/approve_knowledge_for_testing.py --clean-approved-prefix --quality-score 75 --apply`
   - cleaned 5 approved titles
   - raised quality for those useful rows to 75

2. `python3 scripts/approve_knowledge_for_testing.py --id a0a19677-4474-482c-960c-754608bc1ce6 --quality-score 80 --apply`
   - approved one useful ingested transcript record

3. `python3 scripts/approve_knowledge_for_testing.py --archive-low-quality --max-quality-score 50 --apply`
   - non-destructively moved 14 low-quality proposed artifacts to `rejected`

No row deletions were performed.

## 5) Post-cleanup audit

- approved count: `11`
- proposed count: `0`
- low-quality approved count: `0`
- statuses now include `approved` + `rejected`
- noisy prompt/test artifacts moved out of proposed queue

## 6) Hermes retrieval quality verification

Post-cleanup prompts tested:

1. `What does Nexus know about ICT silver bullet concepts?`
   - returns partial synthesis with transcript themes + pending research + approved knowledge

2. `What trading videos were recently ingested?`
   - returns transcript_queue summary with statuses

3. `What trading research is available internally?`
   - returns strategies + ticket context + transcript themes + approved knowledge

## 7) Safety checks

- `NEXUS_DRY_RUN=true` unchanged
- no destructive deletes
- no mass blind approval
- no secret output
