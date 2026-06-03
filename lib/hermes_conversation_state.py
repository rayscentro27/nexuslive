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
    # active_recommendation: persists through follow-ups; only set by explicit "My recommendation:" markers
    "active_recommendation": None,
    # last_meaningful_response: last strategic/option/plan response; NOT updated by fallbacks
    "last_meaningful_response": None,
    "last_meaningful_response_summary": None,
    "last_options": [],
    "last_option_map": {},
    "last_tasks": [],
    "last_task_map": {},
    "last_selected_option": None,
    # last_selected_option_number/text: set by mark_option_selected; preserved across follow-ups
    "last_selected_option_number": None,
    "last_selected_option_text": None,
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


def _load_raw_state() -> dict:
    """Load state without staleness check — used for field preservation across follow-ups."""
    try:
        if _STATE_PATH.exists():
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


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
    """Extract numbered items from response text into {1: 'text', 2: 'text', ...}.

    Matches all common formats:
      1. Item text
      1: Item text
      Option 1: Item text
      Task 1: Item text
      * 1. Item text      (bullet-prefixed numbered, e.g. from approval queue output)
    """
    result: dict[int, str] = {}
    patterns = [
        # "* 1. text" or "- 1. text" — bullet-prefixed numbered items
        re.compile(r'^\s*[\*\-•]\s+(\d+)[.:\)]\s+(.+)', re.IGNORECASE),
        # "Option 1: text", "Task 1: text"
        re.compile(r'^\s*(?:option\s*|task\s*)?(\d+)[.:\)]\s+(.+)', re.IGNORECASE),
        # "  1. text" — plain numbered
        re.compile(r'^\s*(\d+)\.\s+(.+)'),
    ]
    for line in text.splitlines():
        for pat in patterns:
            m = pat.match(line)
            if m:
                num = int(m.group(1))
                txt = m.group(2).strip()
                # Strip trailing "—" and approval-queue meta-text
                txt = re.sub(r'\s*—\s*\w.*$', '', txt).strip()
                if 1 <= num <= 20 and len(txt) > 3:
                    result[num] = txt
                break
    return result


def _extract_recommendation(text: str) -> Optional[str]:
    """Extract recommendation text from response.

    Uses explicit markers first, then falls back to first numbered item.
    Never returns the default footer text about approval boundaries.
    """
    # Explicit "My recommendation:" or similar
    explicit_patterns = [
        re.compile(r'(?:my recommendation|recommendation)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
        re.compile(r'(?:i recommend|hermes recommends)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
        re.compile(r'(?:best move|top move|priority)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
    ]
    for pat in explicit_patterns:
        m = pat.search(text)
        if m:
            rec_text = m.group(1).strip()
            # Stop at the approval boundary line
            rec_lines = []
            for l in rec_text.splitlines():
                if "approval boundary" in l.lower() or "i will not publish" in l.lower():
                    break
                if l.strip():
                    rec_lines.append(l.strip())
                if len(rec_lines) >= 2:
                    break
            candidate = " ".join(rec_lines)[:400]
            # Don't return generic footer text
            if candidate and "approval" not in candidate.lower()[:30]:
                return candidate

    # Fallback: first numbered item is the top recommendation
    numbered = _extract_numbered_list(text)
    if numbered:
        return numbered.get(1) or next(iter(numbered.values()))

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


# ── Fallback / meaningful response detection ──────────────────────────────────

# These body markers identify responses that must NOT overwrite last_meaningful_response
# or active_recommendation — fallbacks, task-missing, and clarification-only responses.
_FALLBACK_BODY_MARKERS = [
    "i don't have task",
    "i don't have the option list",
    "i don't have a previous response",
    "i don't have a recent recommendation",
    "please ask me a question",
    "try: 'how do we make money",
    "try asking:",
    "i wasn't able to generate",
    "quality response",
    "plain-language mode enabled",
    "i need clarification",
    "ask me a question first",
    "please ask me",
]

# Response headers that are informational (correction, clarification) but are NOT
# strategic plan/option responses. They must not overwrite last_meaningful_response
# even though they don't contain typical fallback body text.
_NON_STRATEGIC_HEADERS = frozenset({
    "CORRECTING COURSE",
    "I NEED CLARIFICATION",
})


def _is_meaningful_strategic_response(text: str) -> bool:
    """Return True if this response should update last_meaningful_response.

    Fallback, task-missing, clarification-only, and correction responses do NOT
    qualify. Only strategic/plan/option responses update last_meaningful_response.
    """
    if not text or len(text.strip()) < 30:
        return False
    # Non-strategic headers (correction, clarification) never replace last strategic plan
    first_line = text.strip().splitlines()[0].strip().upper()
    if first_line in _NON_STRATEGIC_HEADERS:
        return False
    text_lower = text.strip().lower()
    return not any(m in text_lower for m in _FALLBACK_BODY_MARKERS)


def _extract_explicit_recommendation(text: str) -> Optional[str]:
    """Extract ONLY explicitly marked recommendations (no fallback to numbered items).

    Used for active_recommendation so it is not accidentally set from a fallback.
    """
    explicit_patterns = [
        re.compile(r'(?:my recommendation|recommendation)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
        re.compile(r'(?:i recommend|hermes recommends)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
        re.compile(r'(?:best move|top move|priority)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
    ]
    for pat in explicit_patterns:
        m = pat.search(text)
        if m:
            rec_text = m.group(1).strip()
            rec_lines = []
            for line in rec_text.splitlines():
                if "approval boundary" in line.lower() or "i will not publish" in line.lower():
                    break
                if line.strip():
                    rec_lines.append(line.strip())
                if len(rec_lines) >= 2:
                    break
            candidate = " ".join(rec_lines)[:400]
            if candidate and "approval" not in candidate.lower()[:30]:
                return candidate
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

    Preserves option maps, task maps, recommendation, and selected option text
    across follow-up responses so "WHAT WAS TASK 1" works after "LETS DO 1",
    and simplify/explain use the last meaningful response rather than a fallback.
    """
    # Load raw existing state for field preservation (no stale check — preserve is safe)
    existing = _load_raw_state()
    now = _now_iso()

    numbered = _extract_numbered_list(hermes_response)
    new_rec = _extract_recommendation(hermes_response)
    explicit_rec = _extract_explicit_recommendation(hermes_response)
    is_meaningful = _is_meaningful_strategic_response(hermes_response)

    # Option/task maps: preserve existing when new response has no numbered items
    if numbered:
        option_map = {str(k): v for k, v in numbered.items()}
        options_list = [v for _, v in sorted(numbered.items())]
    else:
        option_map = existing.get("last_option_map") or {}
        options_list = existing.get("last_options") or []

    # Recommendation: preserve existing when new response has no recommendation
    recommendation = new_rec or existing.get("last_recommendation")

    # Active recommendation: only update from explicit "My recommendation:" markers
    active_rec = (
        explicit_rec
        or existing.get("active_recommendation")
        or recommendation
    )

    # Meaningful response: only update for strategic/plan/option responses, not fallbacks
    if is_meaningful:
        meaningful_response = hermes_response[:2000]
        meaningful_summary = _summarize_response(hermes_response)
    else:
        meaningful_response = existing.get("last_meaningful_response") or hermes_response[:2000]
        meaningful_summary = (
            existing.get("last_meaningful_response_summary")
            or _summarize_response(hermes_response)
        )

    # Preserve selected option data set by mark_option_selected
    selected_option_number = existing.get("last_selected_option_number")
    selected_option_text = existing.get("last_selected_option_text")
    selected_option = existing.get("last_selected_option")

    state = dict(_STATE_SCHEMA)
    state.update({
        "last_user_message": user_message[:500],
        "last_hermes_response_summary": _summarize_response(hermes_response),
        "last_hermes_response_full": hermes_response[:2000],
        "last_recommendation": recommendation,
        "active_recommendation": active_rec,
        "last_meaningful_response": meaningful_response,
        "last_meaningful_response_summary": meaningful_summary,
        "last_options": options_list,
        "last_option_map": option_map,
        "last_tasks": options_list,
        "last_task_map": option_map,
        "last_selected_option": selected_option,
        "last_selected_option_number": selected_option_number,
        "last_selected_option_text": selected_option_text,
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


def mark_option_selected(number: int, text: Optional[str] = None) -> None:
    """Record that Ray selected a specific option, preserving the option text.

    Uses _load_raw_state so selection data is never lost to a stale-check race.
    """
    state = _load_raw_state() or dict(_STATE_SCHEMA)
    state["last_selected_option"] = number
    state["last_selected_option_number"] = number
    if text:
        state["last_selected_option_text"] = text
    state["updated_at"] = _now_iso()
    save_conversation_state(state)


def get_active_recommendation() -> Optional[str]:
    """Return the active recommendation that persists through follow-up responses."""
    state = load_conversation_state()
    return state.get("active_recommendation") or state.get("last_recommendation")


def get_last_meaningful_response() -> Optional[str]:
    """Return the last meaningful strategic response (never a fallback message)."""
    state = load_conversation_state()
    return state.get("last_meaningful_response") or state.get("last_hermes_response_full")


def get_selected_option_context() -> tuple:
    """Return (number, text) of the last option Ray selected. Both may be None."""
    state = load_conversation_state()
    return state.get("last_selected_option_number"), state.get("last_selected_option_text")


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
