# Hermes NotebookLM Commands

## Refinements Added
- Extended NotebookLM intent keywords in `lib/hermes_runtime_config.py`.
- Extended NotebookLM handling in `lib/hermes_internal_first.py`.

## Commands Covered
- "List NotebookLM notebooks"
- "Sync forex notebook" (dry-run)
- "Sync all enabled notebooks" (queued task for long-running work)
- "What did NotebookLM learn?" (queue/intake summary path)
- "Show notebook sync status"
- "What NotebookLM knowledge is pending review?" (status + queue context)

## Behavior Guarantees
- Supabase-first/queue-first operational responses preserved.
- No credential exposure in Hermes replies.
- No automatic Telegram summary sends.
- Long-running multi-notebook sync uses `ai_task_queue` task creation.

## Known Gap
- Notebook-specific semantic summaries (e.g., grants summary by notebook id) need authenticated CLI data to provide live notebook-derived output.
