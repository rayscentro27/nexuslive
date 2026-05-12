# Telegram Session Memory Audit
**Date:** 2026-05-11  
**Scope:** Hermes conversational context loss investigation

---

## Root Cause

Every Telegram message is handled as a completely independent request.

### `_conversational_reply(raw: str)` — the exact gap

```python
payload = {
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw},   # ← only current message
    ]
}
```

The `raw` argument contains the current user message only. No history is passed.

---

## Where Context Is Lost

| Location | Issue |
|---|---|
| `_conversational_reply(raw)` | Signature takes only `raw` — no chat_id, no history |
| `handle_inbound_message(text)` | Receives only `text`, not `chat_id` |
| `ops_memory["last_user_instruction"]` | Only stores last message as a string (no turns) |
| `TelegramRouter.conversational_reply` | Bound to `self._conversational_reply` — no context threading |
| `try_internal_first(raw)` | Stateless keyword match — correct, no history needed here |

---

## What Exists (Correctly)

- **`hermes_ops_memory`**: Operational task/plan/approval state. Correctly persists work sessions. Not designed for conversational history.
- **`last_user_instruction`**: Single-string last message. Useful for ops context but not conversational threading.
- **`chat_cooldowns[chat_id]`**: Per-chat rate limiting. `chat_id` is available in `handle_update()` but not passed downstream.
- **Internal-first routing**: Stateless and correct. No history needed for topic-matched answers.

---

## Message Flow (Before Fix)

```
Telegram update
  → handle_update(update)            # has chat_id ✓
    → handle_inbound_message(text)   # no chat_id ✗
      → _conversational_reply(raw)   # stateless ✗
        → OpenRouter: [system + user]  # no history ✗
```

---

## Impact

- "Which one?" → LLM has no idea what "one" refers to
- "Continue" → treated as fresh message, no context
- "What about Claude?" → LLM doesn't know previous provider discussion
- "Why?" → question without subject
- "Compare them" → no referents
- Operational conversation requires repeating context every message

---

## Files Reviewed

| File | Role | Session-aware? |
|---|---|---|
| `telegram_bot.py` | Main bot, message dispatch | No |
| `lib/hermes_internal_first.py` | Topic-matched routing | N/A (stateless by design) |
| `lib/hermes_ops_memory.py` | Operational state persistence | No (single `last_user_instruction`) |
| `lib/hermes_gate.py` | Outbound send gate | N/A |
| `lib/telegram_router.py` | Message classification router | No |
| `lib/hermes_runtime_config.py` | Keyword config | N/A |
