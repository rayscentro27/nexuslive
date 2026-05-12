# Operational Identity Enforcement Audit
**Date:** 2026-05-12  
**Scope:** Where Hermes leaks generic AI behavior — root causes, fixes applied, remaining gaps

---

## Summary Finding

Hermes's identity is defined in the right places but the LLM fallback path (OpenRouter) was not receiving live Nexus operational context — only conversation history. This caused responses that felt generic because the model had no Nexus state to anchor to. Two fixes applied this session.

---

## 1. Identity Definition Points (Where Persona Lives)

| Location | System Prompt / Persona |
|---|---|
| `telegram_bot.py:497-508` | "You are Hermes, AI Chief of Staff for the Nexus platform" — 7 operational rules |
| `lib/hermes_model_router.py:75` | "You are Hermes, the AI Chief of Staff for a business intelligence system" — more generic |
| `try_internal_first()` | Keyword-routed replies with no LLM — identity baked into reply text |
| `render_chat_response()` | Format wrapper — no identity enforcement |

**Root cause of leakage:** `hermes_model_router.py` uses "business intelligence system" — not "Nexus." Any code path using `hermes_model_router.py` for completions gets a less specific identity.

---

## 2. Where Generic Behavior Leaks Through

### Leak 1: No Nexus context in LLM prompt (FIXED)
**Before:** LLM received system_prompt + conversation history. No live Nexus state.  
**Effect:** When asked about Nexus state, LLM had nothing to anchor to → generic reasoning → generic-feeling answer.  
**Fix applied:** `_build_ops_context_snippet()` now appends to the system_prompt:
- Pending approvals count
- Last completed task
- NotebookLM queue size
- Provider status

### Leak 2: Weak fallback message (FIXED)
**Before:** `"I'm online, but my chat model is unavailable right now."`  
**Effect:** Sounds like a generic service status message, not an operational assistant.  
**Fix applied:** `"Hermes is online — conversational model unavailable right now. Try /status, /models, or ask a specific operational question."`

### Leak 3: History window was full (FIXED)
**Before:** `messages.extend(history)` — full history regardless of whether it's a follow-up.  
**Effect:** On long conversations, early unrelated context fragments diluted identity.  
**Fix applied:** Follow-ups get last 6 turns, new questions get last 3 turns.

### Leak 4: hermes_model_router.py persona is generic (OPEN)
**Status:** Not fixed — used for non-Telegram paths (background workers, strategy analysis).  
**Impact:** Low — operator doesn't interact with this path directly.  
**Recommended fix:** Change "business intelligence system" → "Nexus — Raymond's private business and credit intelligence platform."

### Leak 5: render_chat_response() has no identity layer (OPEN)
**Status:** Not fixed — render_chat_response formats text but doesn't add identity guardrails.  
**Impact:** Low — it's a format wrapper, not a generation path.

### Leak 6: Internal-first misses cover generic fallback territory (OPEN)
**Status:** Not fixed — topics like "what's the plan," "what should I know," "give me a brief" have no internal-first match, fall to LLM.  
**Recommended fix:** Add 3-5 more keywords or a "catch-broad" category that routes to `_cmd_data_source_summary()`.

---

## 3. Fixes Applied

| Fix | File | Effect |
|---|---|---|
| Added `_build_ops_context_snippet()` | `telegram_bot.py:183-212` | Injects live Nexus state into every LLM call |
| Strengthened system_prompt | `telegram_bot.py:497-508` | "NOT a generic assistant. ONLY answer in context of Nexus." |
| Improved fallback message | `telegram_bot.py:529-530` | Operational language, suggests specific commands |
| Capped history window | `telegram_bot.py:509-512` | Follow-ups: 6 turns, new: 3 turns — reduces dilution |

---

## 4. Conversational Naturalness Assessment

### What works well
- Short reply enforcement (2-4 sentences, 700 char limit) is effective
- Internal-first returns operational facts directly (no LLM formatting artifacts)
- Greeting detection resets session cleanly

### What still needs improvement
- Internal-first replies for `funding`, `travel`, `marketing` topics are thin — feel like database lookups, not conversational responses
- Follow-up detection is computed but not verbalized — Hermes doesn't say "regarding what we discussed earlier..."
- No "I'm thinking about this operationally" framing when LLM is reasoning

### Target behavior
Ask: "What should I focus on today?"  
**Good:** "Push the invite email fix live — that unblocks tester onboarding. After that, harden the trading config flags. Both are under 2 hours."  
**Bad:** "Here are some general priorities to consider for today: 1. Review your goals. 2. Focus on high-impact tasks..."

The system prompt and operational context injection now point toward the "good" pattern.

---

## 5. Test Results (Post-Fix)

| Suite | Tests | Result |
|---|---|---|
| `test_hermes_telegram_pipeline.py` | 71 | ✅ 71/71 |
| `test_hermes_internal_first.py` | 13 | ✅ 13/13 |
| `test_hermes_conversation_memory.py` | 29 | ✅ 29/29 |
