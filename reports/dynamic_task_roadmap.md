# Dynamic Task Roadmap

Date: 2026-05-15

Roadmap system implemented with a living state file:
- `roadmap/nexus_dynamic_roadmap.json`

Roadmap capabilities:
- evolving status model (`queued`, `active`, `paused`, `blocked`, `review`, `completed`)
- dynamic priority ordering (`priority_score`)
- operational impact + rationale per task
- worker recommendation per task
- blocker tracking
- next discussion prompt per task
- lessons continuity log

Execution integration:
- "Hermes do task X" dispatches into `ai_task_queue` via `lib/ai_task_dispatch.py`
- roadmap task is linked to dispatch task id and marked active

Seeded with 30 high-value tasks across requested categories.
