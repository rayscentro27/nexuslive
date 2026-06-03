"""
hermes_conversation_state.py
Phase 7B: Conversation context manager for Hermes CFO Brain.

Stores the last user message, Hermes response, options, tasks, and
recommendations so follow-up messages resolve correctly:
  "WHAT WAS TASK 1"  → last_task_map[1]
  "LET'S DO 1"       → last_option_map[1]
  "SIMPLIFY THAT"    → last_hermes_response_full
  "EXPLAIN THAT"     → last_recommendation

Safety: saves summaries only — no credentials, no secrets, no raw payloads.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_STRATEGY_DIR = _ROOT / "docs" / "reports" / "strategy"
_TRAINING_DIR = _ROOT / "docs" / "reports" / "training"

_STATE_PATH   = _STRATEGY_DIR / "hermes_conversation_state.json"
_HISTORY_PATH = _STRATEGY_DIR / "hermes_conversation_history.jsonl"

STALE_AFTER_HOURS = 24

_STATE_SCHEMA: dict = {
    "last_user_message": None,
    "last_hermes_response_summary": None,
    "last_hermes_response_full": None,
    "last_recommendation": None,
    "last_options": [],
    "last_option_map": {},
    "last_tasks": [],
    "last_task_map": {},
    "last_selected_option": None,
    "last_tool_used": None,
    "last_artifact_path": None,
    "last_approval_item": None,
    "last_research_gap_id": None,
    "last_scout_assignment_id": None,
    "last_prompt_generated": None,
    "current_topic": None,
    "created_at": None,
    "updated_at": None,
    "stale_after_hours": STALE_AFTER_HOURS,
}


# ── IO helpers ────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_stale(state: dict) -> bool:
    updated = state.get("updated_at") or state.get("created_at")
    if not updated:
        return True
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(
            updated.replace("Z", "+00:00")
        )
        return age > timedelta(hours=state.get("stale_after_hours", STALE_AFTER_HOURS))
    except Exception:
        return True


def load_conversation_state() -> dict:
    """Load persisted conversation state. Returns empty schema if stale or missing."""
    try:
        if _STATE_PATH.exists():
            data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
            if not _is_stale(data):
                return data
    except Exception:
        pass
    return dict(_STATE_SCHEMA)


def save_conversation_state(state: dict) -> None:
    """Persist conversation state to disk."""
    try:
        _STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning("save_conversation_state error: %s", exc)


def _append_history(user_message: str, hermes_response: str, tool_used: Optional[str]) -> None:
    """Append one interaction to the conversation history JSONL."""
    try:
        _STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": _now_iso(),
            "user": user_message[:400],
            "hermes_summary": _summarize_response(hermes_response),
            "tool": tool_used,
        }
        with _HISTORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("_append_history error: %s", exc)


# ── Response parsers ──────────────────────────────────────────────────────────

def _summarize_response(text: str) -> str:
    """Return a short summary of a Hermes response (first 300 non-blank chars)."""
    if not text:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " | ".join(lines[:4])[:300]


def _extract_numbered_list(text: str) -> dict[int, str]:
    """Extract numbered items from response text into {1: 'text', 2: 'text', ...}."""
    result: dict[int, str] = {}
    # Match "1. text", "1: text", "Option 1: text", "Task 1: text", "  1. text"
    patterns = [
        re.compile(r'^\s*(?:option\s*|task\s*)?(\d+)[.:\)]\s+(.+)', re.IGNORECASE),
        re.compile(r'^\s*(\d+)\.\s+(.+)'),
    ]
    for line in text.splitlines():
        for pat in patterns:
            m = pat.match(line)
            if m:
                num = int(m.group(1))
                txt = m.group(2).strip()
                if 1 <= num <= 20 and txt:
                    result[num] = txt
                break
    return result


def _extract_recommendation(text: str) -> Optional[str]:
    """Extract recommendation text from response."""
    patterns = [
        re.compile(r'(?:my recommendation|recommendation)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
        re.compile(r'(?:i recommend|hermes recommends)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            # Take first 2 lines of recommendation
            rec_text = m.group(1).strip()
            rec_lines = [l.strip() for l in rec_text.splitlines() if l.strip()]
            return " ".join(rec_lines[:2])[:400]
    return None


def _extract_topic(message: str, text: str) -> Optional[str]:
    """Infer current_topic from the response header."""
    first_line = (text or "").strip().splitlines()
    if first_line:
        header = first_line[0].strip().upper()
        for keyword in ["NEXUS PLAN", "REVENUE", "APPROVAL", "RESEARCH QUEUE",
                        "IMPLEMENTATION PROMPT", "SCOUT", "MONEY", "WEEKLY",
                        "MORNING", "TASK", "PLAIN ANSWER", "OPTION SELECTED"]:
            if keyword in header:
                return keyword.lower().replace(" ", "_")
    msg_lower = (message or "").lower()
    if any(k in msg_lower for k in ["money", "revenue", "earn", "make money"]):
        return "money_strategy"
    if any(k in msg_lower for k in ["task", "queue", "pending"]):
        return "task_queue"
    if any(k in msg_lower for k in ["daily", "morning", "today"]):
        return "daily_cycle"
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def update_conversation_state(
    user_message: str,
    hermes_response: str,
    tool_used: Optional[str] = None,
    approval_item: Optional[str] = None,
    research_gap_id: Optional[str] = None,
    scout_assignment_id: Optional[str] = None,
    prompt_generated: Optional[str] = None,
    artifact_path: Optional[str] = None,
) -> dict:
    """Parse the Hermes response and persist conversation state.

    Called after every Hermes response so follow-ups can reference context.
    """
    state = dict(_STATE_SCHEMA)
    now = _now_iso()

    numbered = _extract_numbered_list(hermes_response)
    options_list = [v for _, v in sorted(numbered.items())]
    tasks_list = list(options_list)  # Same extraction, context determines meaning

    state.update({
        "last_user_message": user_message[:500],
        "last_hermes_response_summary": _summarize_response(hermes_response),
        "last_hermes_response_full": hermes_response[:2000],
        "last_recommendation": _extract_recommendation(hermes_response),
        "last_options": options_list,
        "last_option_map": {str(k): v for k, v in numbered.items()},
        "last_tasks": tasks_list,
        "last_task_map": {str(k): v for k, v in numbered.items()},
        "last_tool_used": tool_used,
        "last_artifact_path": artifact_path,
        "last_approval_item": approval_item,
        "last_research_gap_id": research_gap_id,
        "last_scout_assignment_id": scout_assignment_id,
        "last_prompt_generated": prompt_generated,
        "current_topic": _extract_topic(user_message, hermes_response),
        "created_at": now,
        "updated_at": now,
        "stale_after_hours": STALE_AFTER_HOURS,
    })

    save_conversation_state(state)
    _append_history(user_message, hermes_response, tool_used)
    return state


def get_option(number: int) -> Optional[str]:
    """Look up option N from the last response."""
    state = load_conversation_state()
    opt_map = state.get("last_option_map") or {}
    return opt_map.get(str(number)) or opt_map.get(number)


def get_task(number: int) -> Optional[str]:
    """Look up task N from the last response."""
    state = load_conversation_state()
    task_map = state.get("last_task_map") or {}
    return task_map.get(str(number)) or task_map.get(number)


def get_last_recommendation() -> Optional[str]:
    """Return the recommendation from the last Hermes response."""
    return load_conversation_state().get("last_recommendation")


def get_last_response_full() -> Optional[str]:
    """Return the full text of the last Hermes response."""
    return load_conversation_state().get("last_hermes_response_full")


def get_last_response_summary() -> Optional[str]:
    """Return the summary of the last Hermes response."""
    return load_conversation_state().get("last_hermes_response_summary")


def mark_option_selected(number: int) -> None:
    """Record that Ray selected a specific option."""
    state = load_conversation_state()
    state["last_selected_option"] = number
    state["updated_at"] = _now_iso()
    save_conversation_state(state)


def has_active_context() -> bool:
    """Return True if there is non-stale conversation context."""
    state = load_conversation_state()
    return bool(state.get("last_user_message") and not _is_stale(state))


def get_recent_history(n: int = 5) -> list[dict]:
    """Return last N history entries."""
    try:
        if not _HISTORY_PATH.exists():
            return []
        lines = _HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            if len(entries) >= n:
                break
        return list(reversed(entries))
    except Exception:
        return []
