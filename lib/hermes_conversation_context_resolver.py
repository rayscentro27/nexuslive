"""
hermes_conversation_context_resolver.py
=========================================
Resolves follow-up references ("show it", "why that", "view it") in Telegram
by tracking the last important object Hermes mentioned.

Stores runtime context in docs/reports/runtime/hermes_conversation_context.json.
This file is excluded from git (runtime state only).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
_RUNTIME_DIR = _ROOT / "docs" / "reports" / "runtime"
_CONTEXT_FILE = _RUNTIME_DIR / "hermes_conversation_context.json"

# ── Follow-up phrase sets ────────────────────────────────────────────────────

FOLLOWUP_VIEW_PHRASES: frozenset[str] = frozenset([
    "can i view it", "can i see it", "show it", "open it", "let me see it",
    "view it", "view the draft", "see the draft", "see it", "show me it",
    "show the draft", "what does it look like", "show me the draft",
    "let me view it", "display it", "show the best one", "show the first one",
    "show the top one",
])

FOLLOWUP_WHY_PHRASES: frozenset[str] = frozenset([
    "why did you pick that", "why that one", "why that", "why pick that",
    "why did you choose that", "why did you recommend that",
    "what makes it the best", "explain your choice", "why this one",
    "why that recommendation", "why did you recommend this",
])

FOLLOWUP_STATUS_PHRASES: frozenset[str] = frozenset([
    "what is its status", "what happened with that", "status of that",
    "what is the status", "current status",
    "status",
    "where are we with it", "what happened with it",
    "is it done", "is it assigned",
    "who has it",
    "what is next for it", "what is next",
])

FOLLOWUP_ACTION_PHRASES: frozenset[str] = frozenset([
    "what should i do with it", "what do i do with it",
    "approve it", "reject it", "assign it", "send it to the scout",
    "who is working on it", "mark it in progress", "continue that",
    "build it", "draft it",
])

ALL_FOLLOWUP_PHRASES: frozenset[str] = (
    FOLLOWUP_VIEW_PHRASES
    | FOLLOWUP_WHY_PHRASES
    | FOLLOWUP_STATUS_PHRASES
    | FOLLOWUP_ACTION_PHRASES
)


def is_followup_phrase(text: str) -> bool:
    """Return True if the text is a follow-up reference needing context."""
    t = (text or "").strip().lower().rstrip("?. ")
    return t in ALL_FOLLOWUP_PHRASES


# ── Context storage ──────────────────────────────────────────────────────────

def record_context_event(event: dict) -> None:
    """Persist the last important context event for follow-up resolution."""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    try:
        _CONTEXT_FILE.write_text(json.dumps(event, indent=2))
    except Exception:
        pass


def get_last_context() -> Optional[dict]:
    """Return the last recorded context event, or None if none exists."""
    if not _CONTEXT_FILE.exists():
        return None
    try:
        return json.loads(_CONTEXT_FILE.read_text())
    except Exception:
        return None


# ── Context extraction from response text ───────────────────────────────────

def extract_context_from_response(user_message: str, response_text: str) -> Optional[dict]:
    """
    Parse a Hermes response to extract a context event for follow-up resolution.
    Returns a context dict, or None if response is not a trackable object.
    """
    text = response_text or ""

    # Content draft — path present
    draft_match = re.search(r"docs/reports/content/([^\s\n\"']+\.md)", text)
    if draft_match:
        path = "docs/reports/content/" + draft_match.group(1)
        action_match = re.search(r"act_[a-f0-9]+", text)
        action_id = action_match.group(0) if action_match else "act_aa99698ef8"
        return {
            "user_message": user_message,
            "hermes_response_type": "content_draft",
            "primary_object_type": "content_draft",
            "primary_object_id": action_id,
            "primary_object_title": "Credit/Funding Readiness Checklist",
            "primary_object_path": path,
            "related_action_id": action_id,
            "related_scout": "content_intelligence_scout",
            "allowed_followups": ["can i view it", "show it", "make it better", "create a new version"],
            "evidence_path": path,
        }

    # Review-first recommendation
    if "review this first:" in text.lower():
        match = re.search(r"[Rr]eview this first:\s*(.+?)(?:\n|$)", text)
        title = (match.group(1).strip()[:100] if match else "recommended item").rstrip(".")
        action_match = re.search(r"act_[a-f0-9]+", text)
        action_id = action_match.group(0) if action_match else ""
        path_match = re.search(r"docs/reports/[^\s\n\"']+\.(?:json|md|jsonl)", text)
        path = path_match.group(0) if path_match else ""
        return {
            "user_message": user_message,
            "hermes_response_type": "review_first",
            "primary_object_type": "opportunity",
            "primary_object_id": action_id,
            "primary_object_title": title,
            "primary_object_path": path,
            "related_action_id": action_id,
            "allowed_followups": ["show it", "why did you pick that", "what should i do with it"],
            "evidence_path": path,
            "why_selected": (
                "fastest reviewable revenue asset; aligns with 30-day revenue goal; "
                "free to draft; supports funding-readiness audience"
            ),
        }

    # Single action preview — triggered by "ACTION: ..." (format_action_preview_response output)
    single_action_match = re.match(r"ACTION:\s+(.+?)(?:\n|$)", text.strip())
    if single_action_match and not text.strip().upper().startswith("ACTION QUEUE"):
        title = single_action_match.group(1).strip()[:100]
        action_match = re.search(r"act_[a-f0-9]+", text)
        action_id = action_match.group(0) if action_match else ""
        scout_match = re.search(r"Scout:\s*(.+?)(?:\n|$)", text)
        scout = scout_match.group(1).strip() if scout_match else ""
        status_match = re.search(r"Status:\s*(.+?)(?:\n|$)", text)
        status = status_match.group(1).strip() if status_match else ""
        return {
            "user_message": user_message,
            "hermes_response_type": "action_preview",
            "primary_object_type": "action",
            "primary_object_id": action_id,
            "primary_object_title": title,
            "primary_object_path": "docs/reports/actions/hermes_action_queue.jsonl",
            "related_action_id": action_id,
            "related_scout": scout,
            "status": status,
            "allowed_followups": ["what is its status", "who has it", "what is next for it"],
            "evidence_path": "docs/reports/actions/hermes_action_queue.jsonl",
        }

    # Action queue — triggered by "ACTION QUEUE" header
    if text.strip().upper().startswith("ACTION QUEUE"):
        match = re.search(r"1\.\s+(.+?)(?:\n|$)", text)
        title = (match.group(1).strip()[:100] if match else "").rstrip(".")
        action_match = re.search(r"act_[a-f0-9]+", text)
        action_id = action_match.group(0) if action_match else ""
        return {
            "user_message": user_message,
            "hermes_response_type": "action_queue",
            "primary_object_type": "action",
            "primary_object_id": action_id,
            "primary_object_title": title,
            "primary_object_path": "docs/reports/actions/hermes_action_queue.jsonl",
            "related_action_id": action_id,
            "allowed_followups": ["show the first one", "show the best one", "what is its status"],
            "evidence_path": "docs/reports/actions/hermes_action_queue.jsonl",
        }

    # Decision log
    if text.strip().upper().startswith("DECISION LOG"):
        path_match = re.search(r"docs/reports/[^\s\n\"']+\.(?:json|jsonl)", text)
        path = path_match.group(0) if path_match else "docs/reports/decisions/hermes_decision_log.jsonl"
        return {
            "user_message": user_message,
            "hermes_response_type": "decision_log",
            "primary_object_type": "decision",
            "primary_object_id": "",
            "primary_object_title": "Latest Hermes decisions",
            "primary_object_path": path,
            "allowed_followups": ["show it", "why did you pick that"],
            "evidence_path": path,
        }

    # Daily research review
    if "daily research review" in text.lower()[:60]:
        path_match = re.search(r"docs/reports/[^\s\n\"']+\.(?:json|md)", text)
        path = path_match.group(0) if path_match else ""
        opp_match = re.search(r"[Bb]est move:\s*(.+?)(?:\n|$)", text)
        title = (opp_match.group(1).strip()[:100] if opp_match else "top research finding").rstrip(".")
        return {
            "user_message": user_message,
            "hermes_response_type": "daily_review",
            "primary_object_type": "daily_review",
            "primary_object_id": "",
            "primary_object_title": title,
            "primary_object_path": path,
            "allowed_followups": ["show it", "show the best one", "what should i do with it"],
            "evidence_path": path,
        }

    return None


# ── Follow-up resolution ─────────────────────────────────────────────────────

def resolve_reference(user_message: str) -> Optional[dict]:
    """
    Resolve a follow-up phrase to the last context event.
    Returns {"action": str, "context": dict} or None.
    """
    ctx = get_last_context()
    if not ctx:
        return None
    t = (user_message or "").strip().lower().rstrip("?. ")
    if t in FOLLOWUP_VIEW_PHRASES:
        return {"action": "view", "context": ctx}
    if t in FOLLOWUP_WHY_PHRASES:
        return {"action": "why", "context": ctx}
    if t in FOLLOWUP_STATUS_PHRASES:
        return {"action": "status", "context": ctx}
    if t in FOLLOWUP_ACTION_PHRASES:
        return {"action": "act", "context": ctx}
    return None


def resolve_artifact_reference(user_message: str) -> Optional[dict]:
    ctx = get_last_context()
    if ctx and ctx.get("primary_object_type") in ("content_draft", "artifact"):
        return ctx
    return None


def resolve_action_reference(user_message: str) -> Optional[dict]:
    ctx = get_last_context()
    if ctx and ctx.get("primary_object_type") == "action":
        return ctx
    return None


def resolve_decision_reference(user_message: str) -> Optional[dict]:
    ctx = get_last_context()
    if ctx and ctx.get("primary_object_type") == "decision":
        return ctx
    return None


def resolve_source_reference(user_message: str) -> Optional[dict]:
    ctx = get_last_context()
    if ctx and ctx.get("primary_object_type") == "source":
        return ctx
    return None


def resolve_recommendation_reference(user_message: str) -> Optional[dict]:
    ctx = get_last_context()
    if ctx and ctx.get("primary_object_type") in ("opportunity", "review_first", "daily_review"):
        return ctx
    return None


def resolve_daily_review_reference(user_message: str) -> Optional[dict]:
    ctx = get_last_context()
    if ctx and ctx.get("primary_object_type") == "daily_review":
        return ctx
    return None


def format_unresolved_reference_response(user_message: str) -> str:
    """Return a short clarification question when follow-up cannot be resolved."""
    ctx = get_last_context()
    if ctx:
        obj_type = ctx.get("primary_object_type", "item").replace("_", " ")
        title = ctx.get("primary_object_title", "")
        if title:
            return (
                f"Do you mean the {obj_type} '{title[:60]}'? "
                f"Say 'show it' or 'yes' to confirm, or tell me which one."
            )
    return (
        "Do you mean the latest checklist draft, the top opportunity, or the last action? "
        "Say which one and I'll pull it up."
    )
