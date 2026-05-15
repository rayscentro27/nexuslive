# Hermes Demo Trading Commands

Date: 2026-05-15

Added conversational retrieval commands in `lib/hermes_supabase_first.py`:
- "What is Sage trading in demo?"
- "How did demo trading perform today?"
- "What did Hermes learn from the last losing trade?"
- "Pause demo trading"
- "Resume demo trading"
- "Show demo trading risk status"

Safety behavior:
- Replies are request/response only.
- No auto Telegram trading summaries added.
- Pause/resume affects demo kill switch state only.
- Real-money trading remains disabled by posture checks.
