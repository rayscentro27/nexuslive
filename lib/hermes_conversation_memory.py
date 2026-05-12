"""
Short-term conversational session memory for Hermes Telegram.

Maintains a rolling per-chat turn history (user + assistant messages) with TTL
expiration. Purely in-memory — no file or database persistence. This is
operational context only, not long-term Knowledge Brain memory.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

_sessions: dict[str, deque] = {}
_lock = threading.Lock()

MAX_TURNS = 20           # max total turns stored (10 user+assistant pairs)
SESSION_TTL_SECONDS = 1800  # 30 min idle → session expires

_FOLLOWUP_TOKENS = frozenset({
    "which one", "that one", "the other", "those", "these", "it", "them",
    "continue", "expand", "go on", "keep going", "tell me more",
    "why", "why not", "because", "how so", "elaborate",
    "compare them", "compare", "vs", "versus",
    "what about", "and claude", "and openrouter", "and ollama",
    "the first", "the second", "the third", "the last",
    "can you", "show me", "which should i", "what's better",
    "best option", "worst", "fastest", "cheapest",
})


def _now() -> float:
    return time.monotonic()


def _prune_expired() -> None:
    """Remove sessions idle beyond TTL. Caller must hold _lock."""
    cutoff = _now() - SESSION_TTL_SECONDS
    stale = [cid for cid, turns in _sessions.items()
             if not turns or turns[-1].get("ts", 0) < cutoff]
    for cid in stale:
        del _sessions[cid]


def record_turn(chat_id: str, role: str, content: str) -> None:
    """Append one turn to the session for chat_id."""
    if not chat_id or not content:
        return
    content = (content or "").strip()[:2000]  # cap individual turn length
    with _lock:
        _prune_expired()
        if chat_id not in _sessions:
            _sessions[chat_id] = deque(maxlen=MAX_TURNS)
        _sessions[chat_id].append({"role": role, "content": content, "ts": _now()})


def get_history(chat_id: str) -> list[dict[str, str]]:
    """Return prior turns as OpenRouter-compatible message dicts, newest-last.

    Returns empty list if session is expired or chat_id is unknown.
    The current user message is NOT included — callers append it themselves.
    """
    if not chat_id:
        return []
    with _lock:
        _prune_expired()
        turns = _sessions.get(chat_id)
        if not turns:
            return []
        cutoff = _now() - SESSION_TTL_SECONDS
        # filter out any individually stale turns (shouldn't normally happen)
        return [
            {"role": t["role"], "content": t["content"]}
            for t in turns
            if t.get("ts", 0) >= cutoff
        ]


def is_followup(text: str, chat_id: str) -> bool:
    """True if this message looks like a follow-up to the prior conversation.

    Criteria: short message (< 60 chars) that contains a referential token
    AND there is existing history for this chat.
    """
    if not chat_id:
        return False
    t = (text or "").strip().lower()
    if len(t) > 60:
        return False
    if not any(tok in t for tok in _FOLLOWUP_TOKENS):
        return False
    with _lock:
        return bool(_sessions.get(chat_id))


def get_last_assistant_reply(chat_id: str) -> str:
    """Return the most recent assistant reply for this chat, or ''."""
    if not chat_id:
        return ""
    with _lock:
        turns = _sessions.get(chat_id)
        if not turns:
            return ""
        for turn in reversed(turns):
            if turn.get("role") == "assistant":
                return turn.get("content", "")
    return ""


def clear_session(chat_id: str) -> None:
    """Explicitly clear the session for chat_id (e.g., on /start or /clear)."""
    if not chat_id:
        return
    with _lock:
        _sessions.pop(chat_id, None)


def session_summary(chat_id: str) -> dict[str, Any]:
    """Return metadata about the current session for diagnostics."""
    with _lock:
        turns = _sessions.get(chat_id) or []
        user_turns = sum(1 for t in turns if t.get("role") == "user")
        age = (_now() - turns[-1]["ts"]) if turns else None
        return {
            "total_turns": len(turns),
            "user_turns": user_turns,
            "idle_seconds": round(age, 1) if age is not None else None,
            "ttl_seconds": SESSION_TTL_SECONDS,
        }
