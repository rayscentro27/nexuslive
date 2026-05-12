# Hermes Telegram Log Forensics & Repair — 2026-05-11

## Root Causes (4 confirmed)

### 1. "What AI providers are available?" → generic public AI list
- **File**: `lib/hermes_runtime_config.py` + `lib/hermes_internal_first.py`
- **Cause**: No "ai_providers" topic in `hermes_internal_first_keywords`. Query fell through to OpenRouter deepseek-chat with bare system prompt ("You are Hermes. Reply naturally and briefly") — model returned generic public AI providers (OpenAI, Google, Anthropic, etc.) because it had no Nexus context.
- **Fix**: Added `ai_providers` topic to keywords (13 phrases including "what AI providers are available", "is Claude available", "is OpenClaw available", "what fallback provider", "model router status"). Added `ai_providers` handler to `hermes_internal_first.py` that reads live env config and returns Nexus-specific provider topology.

### 2. Conversational replies too report-like
- **Files**: `telegram_bot.py` + `lib/hermes_internal_first.py`
- **Cause A**: Internal-first replies prepended "Direct answer:", "Source:", "Next:" as section headers — looked like a report.
- **Cause B**: `_conversational_reply()` appended "Confidence: X\nSource checked: Y" to every internal reply.
- **Cause C**: OpenRouter system prompt gave no operational tone constraint — generic assistant voice.
- **Fix**: Removed report-like prefixes from all 6 internal-first topic handlers. Removed "Confidence/Source" suffix from reply. Improved system prompt with explicit constraints: 2-4 sentence max, no markdown headers, operational Nexus context, no generic public AI, internal-provider-first, conversational tone.

### 3. "What should I focus on today?" falls through internal-first
- **File**: `lib/hermes_runtime_config.py`
- **Cause**: "today" keyword list only had "what should i work on today" and "what should we work on today". "What should I focus on today?" didn't match → fell through to OpenRouter generic call.
- **Fix**: Added 6 additional phrases: "what should i focus on today", "what to focus on today", "focus today", "priorities today", "top priorities".

### 4. Forbidden content not blocked at content level
- **File**: `lib/hermes_gate.py`
- **Cause**: Gate only checked event_type and auto_reports flag. A message containing "🏛️ Nexus Research" or "Key Findings:" could still reach Telegram if sent via `send_direct_response` with an allowed event_type.
- **Fix**: Added `_FORBIDDEN_CONTENT_PATTERNS` list and `_contains_forbidden_content()` filter. Wired into both `send()` and `send_direct_response()` as belt-and-suspenders checks.

---

## Files Changed

| File | What Changed |
|------|-------------|
| `lib/hermes_runtime_config.py` | Added "ai_providers" topic + 13 phrases; added 6 "focus today" variants to "today" topic |
| `lib/hermes_internal_first.py` | Added `ai_providers` handler; removed "Direct answer:" prefix from all 6 topic handlers; conversational formatting |
| `telegram_bot.py` | Removed "Confidence/Source" suffix from internal-first replies; improved system prompt (operational, Nexus-specific, concise, internal-first, max 300 tokens) |
| `lib/hermes_gate.py` | Added `_FORBIDDEN_CONTENT_PATTERNS`, `_contains_forbidden_content()`; wired into `send()` and `send_direct_response()` |
| `scripts/test_hermes_internal_first.py` | Added 9 new tests: ai_providers routing, focus-today routing, no "Direct answer:" prefix |
| `scripts/test_telegram_policy.py` | Added forbidden content filter tests (7 blocked + 4 allowed) |
| `scripts/test_telegram_log_policy.py` | New test file: 36 tests covering all 7 repair phases |

---

## Tests Run

| Suite | Result |
|-------|--------|
| `scripts/test_hermes_internal_first.py` | 13/13 ✅ |
| `scripts/test_telegram_log_policy.py` | 36/36 ✅ |
| `scripts/test_hermes_telegram_pipeline.py` | 71/71 ✅ (no regressions) |
| Policy inline tests | 27/27 ✅ |

---

## Services Restarted

- `com.raymonddavis.nexus.telegram` — restarted via `launchctl kickstart -k`
- Service reconnected: 2026-05-11 14:30:44 — "Telegram connected: @Nexuschosenbot"
- Mode confirmed: manual-only, auto-report suppressed, secondary bots disabled
- 409 conflict resolved (old session expired naturally)

---

## Safety Flags — UNCHANGED ✓

```
TELEGRAM_AUTO_REPORTS_ENABLED=false
TELEGRAM_FULL_REPORTS_ENABLED=false
TELEGRAM_MANUAL_ONLY=true
SWARM_EXECUTION_ENABLED=false
HERMES_CLI_EXECUTION_ENABLED=false
TRADING_LIVE_EXECUTION_ENABLED=false
HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false
```

---

## Expected Behavior After Repair

| Query | Before | After |
|-------|--------|-------|
| "What AI providers are available?" | Generic public AI list (OpenAI, Google, etc.) | Nexus topology: OpenRouter, Ollama, Claude Code, OpenClaw status |
| "Is Claude available?" | Generic → fell through | Routes to ai_providers → Nexus answer |
| "What should I focus on today?" | OpenRouter generic advice | Internal-first: operational Nexus priorities |
| "What should I focus on today?" style | "Direct answer: start with..." | "Today I'd focus on: [specific item]..." |
| Research summary in Telegram | Possibly leaking (no content filter) | Blocked at gate with content filter |
| Conversational tone | Formal, report-prefixed | Short, operational, no headers |

---

## Remaining Notes

1. **Ollama unreachable**: `qwen3:8b` and `llama3.2:3b` both show "Connection refused" in logs — local Ollama tunnel is down. The ai_providers reply correctly documents this.
2. **Oracle VM**: 161.153.40.41 frequently at 100% packet loss — documented in ai_providers reply.
3. **Research summaries**: No actual forbidden content found escaped in `telegram-integration.log`. The scheduler `_notify()` was already blocking via `TELEGRAM_AUTO_REPORTS_ENABLED=false`. The new content filter is a belt-and-suspenders addition.
