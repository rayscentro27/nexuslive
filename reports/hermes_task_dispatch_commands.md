# Hermes Task Dispatch Commands

Date: 2026-05-15

Added Telegram conversational task dispatch handling in `lib/hermes_supabase_first.py`.

Supported commands:
- "Send this to OpenCode"
- "Ask Claude Code to ..."
- "Send this task to OpenClaude"
- "What tasks are running?"
- "Show last OpenCode result"
- "Pause OpenCode tasks"
- "Resume Claude Code queue"

Behavior:
- Creates `ai_task_queue` entries via `lib/ai_task_dispatch.py`
- Assigns target worker
- Tracks queue status and returns conversational summaries
- Preserves Telegram hardening (request/response only, no auto-spam summaries)
