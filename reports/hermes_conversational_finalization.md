# Hermes Conversational Mode Finalization
**Date:** 2026-05-12  
**Scope:** Session memory, conversational reply quality, follow-up detection, Telegram UX

---

## 1. Current Conversational Architecture

```
User message (Telegram)
    ↓
telegram_bot.py → _conversational_reply()
    ↓
hermes_conversation_memory.py (session context retrieval)
    ↓
try_internal_first() (keyword-matched internal routing)
    ↓ [if no match]
OpenRouter / Ollama / Claude fallback (LLM reply)
    ↓
hermes_gate.send_direct_response() (content filter + dedup)
    ↓
Telegram reply
```

---

## 2. Session Memory: Current State

**Module:** `lib/hermes_conversation_memory.py`  
**Store:** In-memory `dict[chat_id → deque(maxlen=20)]`  
**TTL:** 30 minutes per session  
**Follow-up detection:** Yes — `is_followup_message()` checks prior context for topic continuity  

### What's working
- Session store is active — messages accumulate within conversation window
- Follow-up detection uses prior context to avoid re-summarizing context already given
- 20-message window is appropriate for operational conversations
- 30-minute TTL prevents stale context from bleeding across sessions

### What's not working
- **Memory is not persisted** — bot restart clears all sessions (known, acceptable)
- **No session summary on TTL expiry** — context just evaporates, no graceful handoff message
- **No cross-topic memory** — if user switches from "funding" to "travel" and back, no memory of prior funding topic in same session
- **Memory not passed to LLM fallback** — when OpenRouter handles a reply, it does not receive prior conversation turns as context

---

## 3. Follow-up Detection: Assessment

**Function:** `is_followup_message(chat_id, text)` in `hermes_conversation_memory.py`

Current follow-up signals:
- Message is short (< 20 chars)
- Contains pronouns: "it", "that", "this", "those", "they"
- Contains continuation phrases: "and also", "what about", "tell me more"

**Gap:** Follow-up detection does not inform the LLM reply. It's computed but not injected into the prompt or used to adjust internal-first reply text. This means Hermes answers follow-ups as if they were fresh questions.

**Fix:** When `is_followup()` returns True, prepend a brief context note to the LLM prompt:
```python
if is_followup:
    context_prefix = f"[Context: user's prior topic was '{last_topic}'. This is a follow-up.]"
```

---

## 4. Internal-First Coverage (as of 2026-05-12)

| Topic | Keyword Count | Quality |
|---|---|---|
| opencode | 3 | ✅ Good |
| funding | 3 | ✅ Good |
| today | 9 | ✅ Good |
| knowledge_email | 11 | ✅ Good |
| marketing | 3 | ⚠️ Thin |
| travel | 3 | ⚠️ Thin |
| notebooklm | 9 | ✅ Good (fixed 2026-05-12) |
| ai_providers | 15 | ✅ Excellent |
| (no match) | — | Falls through to LLM |

**Gaps in keyword coverage:**
- "status" alone → no match (common operator query)
- "what's happening" → no match
- "morning" / "good morning" → no match (common conversation opener)
- "who are we waiting on" → no match (approvals/blockers query)
- "what did hermes say" / "last message" → no match (session recall)

---

## 5. Reply Quality by Topic

### Strengths
- `ai_providers` — detailed, accurate, lists all known routes
- `today` — pulls from operational memory + recommendations + pending approvals
- `knowledge_email` — fixed (correct count, correct terminology)
- `notebooklm` — fixed (correct routing)
- `funding` — pulls live from Supabase knowledge brain

### Weaknesses
- `travel` / `marketing` — thin replies, mostly "check X file" without summaries
- `opencode` — shows last 3 completed tasks but no active queue context
- No graceful "I don't know" reply — LLM fallback can hallucinate when Ollama is down

---

## 6. LLM Fallback Chain: Current State

Order of fallback:
1. OpenRouter (deepseek-chat) — if `OPENROUTER_API_KEY` set ✅ usually available
2. Hermes local Ollama (qwen3:8b) — requires tunnel to local Mac Mini 
3. Oracle VM Ollama (qwen2.5:14b) — 161.153.40.41, frequently unreachable
4. Claude Code CLI — for code tasks only, not conversational

**Known issue:** When Ollama is unreachable and OpenRouter fails (rate limit / outage), bot returns empty reply. No graceful degradation message is sent.

**Fix:** Add final fallback text:
```python
FALLBACK_UNAVAILABLE = (
    "Hermes is temporarily offline — all AI providers unreachable. "
    "Check /models for status or try again in 2 minutes."
)
```

---

## 7. Session Memory Improvements (Recommended)

### Improvement 1 — Pass last 3 turns to LLM
When calling OpenRouter, include prior turns as system context:
```python
messages = [{"role": "system", "content": system_prompt}]
for turn in session_memory.get_last_n(chat_id, 3):
    messages.append({"role": turn["role"], "content": turn["text"]})
messages.append({"role": "user", "content": current_message})
```

### Improvement 2 — Topic tagging per turn
Tag each turn with matched_topic from `try_internal_first()`:
```python
session_memory.add_turn(chat_id, role="user", text=msg, topic=matched_topic)
```
This enables "what were we just discussing?" replies.

### Improvement 3 — Session summary on expiry
When 30-min TTL fires, write a one-line session summary to ops memory:
```python
"Last session: discussed {topics}, {n} turns, ended at {time}"
```

---

## 8. Telegram UX Assessment

| UX Factor | Status | Notes |
|---|---|---|
| Reply latency | ✅ Good | Internal-first: <100ms. OpenRouter: 2-4s |
| Message length | ✅ Good | Truncated to mode limits |
| Reply formatting | ⚠️ Inconsistent | Some topics use bullets, some use flat text |
| Error handling | ⚠️ Weak | Silent failures when all providers down |
| Follow-up continuity | ⚠️ Partial | Detected but not used |
| Typing indicator | ⚠️ Unknown | Not confirmed present in bot code |

---

## 9. Recommended Implementation Order

1. **Add graceful "all providers offline" fallback reply** — 10 minutes, zero risk
2. **Pass last 3 turns to LLM calls** — 30 minutes, reduces hallucination
3. **Inject follow-up context into LLM prompt** — 20 minutes, improves continuity
4. **Add 3-4 missing keywords** ("status", "morning", "what's happening") — 10 minutes
5. **Standardize reply formatting** (all internal-first topics → bullets) — 30 minutes

---

## 10. Operational Posture

**Conversational mode readiness: 7/10**

The system handles the primary use cases reliably (operational queries, status checks, knowledge retrieval). Gaps are in edge cases (provider failures, follow-up continuity, cold-start openers). These are quality-of-life improvements, not blockers for operational use.
