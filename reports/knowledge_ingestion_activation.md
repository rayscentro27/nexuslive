# Knowledge Ingestion Activation

Date: 2026-05-10

## Activation Scope
- Keep ingestion active in safe DRY RUN mode.
- Parse inbound knowledge emails and extract URLs, categories, tags, notes, and priority.
- Produce proposed KB records and action items in report outputs.

## Safety Guardrails
- `HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false` remains unchanged.
- No automatic persistent Knowledge Brain writes in this activation pass.
- Intake is report-first and operator-review-first.

## Workflow
email intake -> url extraction -> categorization -> queue/proposal -> summary report -> optional later approval

## Coverage
- websites
- YouTube links
- funding research
- marketing research
- trading research
- grants and opportunities

## Status
- Activation validated against existing intake/test scaffolding.
