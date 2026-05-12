# Knowledge Brain Adapter Status

Date: 2026-05-10

## Current State
- Existing adapter and intake scaffolding are already present and stable.
- Dry-run behavior remains enforced for email knowledge intake proposals.

## Safety Defaults
- `HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false`
- Knowledge email intake remains report/proposal-first.

## Proposed Record Shape (confirmed)
- `source_url`
- `source_type`
- `category`
- `title`
- `summary`
- `key_takeaways`
- `action_items`
- `confidence`
- `dry_run`
- `source_email_id`
- `dedup_key`
- `status`

## Deduplication
- Existing dedupe logic remains active in knowledge processing paths.
- Proposed records continue to include deterministic dedup keys.

## Retrieval Validation
- Knowledge and telemetry-adjacent tests remain passing in this execution pass.

## Notes
- No destructive schema redesign was applied.
- Adapter remains additive and compatible with current reports/intelligence flows.
