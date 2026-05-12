# Telegram Log Forensics — 2026-05-11

## Log Files Checked

| File | Size | Last Modified | Status |
|------|------|--------------|--------|
| `nexus-ai/telegram-integration.log` | 16.8 MB | 2026-05-11 14:00 | PRIMARY — all routes logged |
| `nexus-ai/hermes_claude_bot.log` | 631 KB | 2026-05-06 19:37 | Secondary bot — inactive since May 6 |
| `nexus-ai/logs/telegram-bot.log` | empty | — | Unused log path |
| `nexus-ai/logs/scheduler.log` | — | 2026-05-11 13:44 | Scheduler activity |
| `nexus-ai/openclaw/logs/telegram.log` | — | 2026-03-09 | Old log, inactive |
| `nexus-ai/openclaw/logs/telegram.err.log` | — | — | Empty |
| `nexus-ai/logs/auto_executor.log` | — | 2026-05-11 14:18 | No proposals, clean |

## Exact Message Sources Found

### Research Summary Leaking
- **Source**: No forbidden patterns found in `telegram-integration.log`. The patterns were **blocked by the existing gate** (TELEGRAM_AUTO_REPORTS_ENABLED=false + scheduler `_notify()` early return).
- **Remaining risk**: A message with forbidden *content* (🏛️ Nexus Research, Key Findings:, Sources:) could still reach Telegram if sent via `send_direct_response` with `event_type='command_reply'` — this was not content-filtered until this repair.

### "What AI providers are available?" Generic Answer
- **Source**: `telegram_bot.py::_conversational_reply()` — line 463
- **Path**: `try_internal_first()` returns None (no "ai_providers" topic) → OpenRouter deepseek-chat with bare system prompt "You are Hermes. Reply naturally and briefly for Telegram chat." → model answers with generic public AI list.
- **Root cause**: No Nexus-specific context in system prompt; no internal-first handler for provider queries.

### Conversational Replies Too Report-Like
- **Source**: `telegram_bot.py::_conversational_reply()` + `lib/hermes_internal_first.py`
- **Path 1**: `try_internal_first()` replies prepended "Direct answer:", "Source:", "Next:" as headers → report-like formatting
- **Path 2**: `_conversational_reply()` passed internal reply with "Confidence: X\nSource checked: Y" appended
- **Path 3**: OpenRouter system prompt gave no operational tone constraints → generic assistant style

### "What should I focus on today?" Falls Through Internal-First
- **Source**: `lib/hermes_runtime_config.py::default_runtime_config()` — "today" keyword list
- **Root cause**: "what should i focus on today" not in keyword list → falls through to OpenRouter generic call

## Code Paths Responsible

| Symptom | File | Function | Line |
|---------|------|----------|------|
| Generic AI provider list | `telegram_bot.py` | `_conversational_reply` | ~463 |
| No internal routing for "focus today" | `lib/hermes_runtime_config.py` | `default_runtime_config` | ~58 |
| Report-like internal-first replies | `lib/hermes_internal_first.py` | all topic handlers | various |
| Report metadata appended to replies | `telegram_bot.py` | `_conversational_reply` | ~472 |
| Forbidden content not content-filtered | `lib/hermes_gate.py` | `send()` + `send_direct_response()` | ~339 |

## Running Services Checked

| Service | PID | Status |
|---------|-----|--------|
| `com.raymonddavis.nexus.telegram` | 14201 | Running — telegram_bot.py --monitor |
| `com.raymonddavis.nexus.scheduler` | 608 | Running — scheduler.py |
| `com.nexus.research-worker` | 584 | Running — JS node worker |
| `com.nexus.hermes-status` | — | NOT running |
| `com.nexus.research-signal-bridge` | 595 | Running — signal bridge |

## Secondary Bots Status
Log entry at 2026-05-11 08:17:52: "Disabled secondary Telegram bots: hermes_status_bot, hermes_claude_bot, scheduler_notifier"

Secondary bots are correctly disabled. Primary bot: TheChosenOne (@Nexuschosenbot).
