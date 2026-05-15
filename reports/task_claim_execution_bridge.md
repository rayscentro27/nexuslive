# Task Claim Execution Bridge

Date: 2026-05-15

Implemented safe claim/execute bridge in:
- `lib/ai_task_dispatch.py`
- `lib/ai_task_worker_bridge.py`

Capabilities:
- Worker polling and claim flow
- Queue claim transition (`queued` -> `running`)
- Results writeback to `ai_task_results`
- Activity logging to `ai_task_activity_log`
- Timeout/stale recovery (`recover_stale_tasks`)
- Concurrency control via env (`AI_TASK_WORKER_CONCURRENCY`)
- Retry-safe claim behavior using status-guarded updates

Safety:
- Approval-gated tasks move to `waiting_review`
- No unrestricted shell execution from Telegram
- No recursive self-task loop logic added
