# Workforce Task Visualization

Date: 2026-05-15

Workforce Office API now includes dispatch-aware data in:
- `GET /api/admin/ai-operations/workforce`

Added payload sections:
- `ai_task_queue`
- `ai_task_workers`
- `ai_task_recent_results`

UI data bridge updates:
- Queue bars now merge `job_queue` + `ai_task_queue` workload
- Activity feed includes `ai_task_results` completion/failure entries

This exposes live coding-task coordination flow for OpenCode, Claude Code, and OpenClaude.
