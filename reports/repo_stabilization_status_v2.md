# Repo Stabilization Status v2

Date: 2026-05-10

## Snapshot
- Repository is heavily dirty with many unrelated modified files.
- Nexus/Hermes work in this pass was isolated to additive files and targeted updates only.

## Safe Staging Strategy
- Stage by scope, not by `git add .`.
- Group A: NotebookLM dry-run integration files.
- Group B: knowledge review queue + admin endpoints.
- Group C: reports/marketing/launch docs.
- Keep unrelated worker/trading/research file changes out of these commits.

## Risk Notes
- Existing modified files across many subsystems increase accidental commit risk.
- Use explicit path-based staging and `git diff -- <path>` review before commit.
