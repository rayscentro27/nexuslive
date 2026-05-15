# AI Worker Definitions

Date: 2026-05-15

Implemented in `lib/ai_task_dispatch.py` (`WORKER_DEFINITIONS`).

Workers:
- `opencode_codex`
- `claude_code`
- `openclaude`

Each worker includes metadata:
- role
- specialties
- capabilities
- allowed actions
- active status
- health status
- concurrency limit
- runtime environment

Routing policy:
- OpenCode/Codex: repo operations, scripts, terminal ops, tests, audits, infra
- Claude Code: UI/UX, architecture, complex feature passes, system design
- OpenClaude: backup review, refinement, fallback implementation, second-pass analysis
