# Real Knowledge Email Validation

Date: 2026-05-10

Target message:
- from: `rayscentro@yahoo.com`
- to: `goclearonline@gmail.com`

## Queue Validation
- Intake rows inspected: `3`
- Sender-matching rows found (`rayscentro@yahoo.com`): `0`
- Current intake entries lacked sender/subject metadata in this shell snapshot.

## Parsed Links / Categories
- Sample inspected rows show:
  - sender: `None`
  - subject: `None`
  - links: `0`
  - category: `funding`

## Hermes Retrieval Check
- Prompt: `What funding research arrived?`
- Routed internal-first to funding knowledge (`INTERNAL_CONFIRMED`).
- Response was generated from existing internal funding intelligence context.

## CEO Report Path Visibility
- CEO brief formatter and executive email path include NotebookLM queue context.
- No auto-store/Supabase ingestion was enabled in this validation.

## Parsing Failures / Gaps
- Could not confirm that a specific real email from `rayscentro@yahoo.com` is represented in queue metadata from this shell pass.
- Recommended follow-up: ensure sender/subject/link metadata is persisted by intake adapter for traceable validation.
