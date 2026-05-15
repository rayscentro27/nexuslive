# AI Task Queue Architecture

Date: 2026-05-15

Created centralized Supabase queue schema in:
- `supabase/migrations/20260515073000_ai_task_dispatch.sql`

Tables:
1. `ai_task_queue`
2. `ai_task_workers`
3. `ai_task_results`
4. `ai_task_activity_log`

`ai_task_queue` includes required fields:
- `id`, `created_by`, `source`, `assigned_worker`, `task_type`, `priority`
- `title`, `instructions`, `status`
- `created_at`, `started_at`, `completed_at`
- `requires_approval`, `repo_target`, `estimated_scope`
- `result_summary`, `error_summary`

Statuses enforced:
- `queued`, `assigned`, `running`, `waiting_review`, `completed`, `failed`, `rejected`, `paused`

Indexes added for queue reads by status/worker and timeline reads by recency.
