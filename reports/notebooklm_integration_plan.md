# NotebookLM Integration Plan (Safe Dry-Run)

Date: 2026-05-10

## Objective
Prepare NotebookLM ingestion pathway for Hermes/Nexus without mutating production intelligence stores.

## Phase A (This Pass)
- Install/test community CLI in isolated environment.
- Add diagnostics script and dry-run adapter.
- Add internal-first query support for NotebookLM intake status.

## Phase B (Next Safe Step)
- Optional operator-triggered CLI execution wrappers.
- Normalize NotebookLM outputs into proposed record schema.
- Continue report-only queue review and manual approval workflow.

## Phase C (Future, Explicit Approval Needed)
- Controlled persistence into Knowledge Brain after approval gates.
- Add per-record review status and operator confirmation paths.

## Non-Goals
- No automated Supabase writes in this pass.
- No background autonomous NotebookLM jobs.
- No changes to safety flags or execution posture.
