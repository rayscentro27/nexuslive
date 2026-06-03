"""
hermes_failure_learning.py
Phase 7B: Failure example collector and training set builder.

When Hermes produces a bad response, log it. When Ray says "that is not what I meant",
log it. Generate test cases from failures.

Files:
  docs/reports/training/hermes_failed_response_examples.jsonl
  docs/reports/training/hermes_response_training_set.jsonl
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_TRAINING_DIR = _ROOT / "docs" / "reports" / "training"
_FAILED_PATH   = _TRAINING_DIR / "hermes_failed_response_examples.jsonl"
_TRAINING_PATH = _TRAINING_DIR / "hermes_response_training_set.jsonl"

_FAILURE_TYPES = {
    "evidence_dump",
    "generic_quality_fallback",
    "wrong_tool",
    "lost_context",
    "failed_followup",
    "too_technical",
    "did_not_assign_scout",
    "did_not_create_prompt",
    "unsafe_action_attempt",
    "duplicate_queue_item",
}
# Public alias for test imports
FAILURE_TYPES = _FAILURE_TYPES

_EVIDENCE_DUMP_MARKERS = [
    "artifact_inventory", "handoff", "Live answer sources:",
    "Confidence:", "Source 1:", "intelligence_division", "scout_status",
    "════════════", "────────────",
]

_GENERIC_FALLBACK_MARKERS = [
    "quality response", "i wasn't sure what you meant",
    "operations submitted", "vague operations",
    "plain-language mode", "plain language mode enabled",
]

_WRONG_TOOL_MARKERS = [
    "today's money plan", "oanda", "trade execution",
    "no verified broker artifact",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ── Failure classification ────────────────────────────────────────────────────

def classify_failure_type(message: str, response: str) -> str:
    """Return the failure type for a message/response pair."""
    resp_lower = response.lower()
    msg_lower = message.lower()

    if any(m.lower() in resp_lower for m in _EVIDENCE_DUMP_MARKERS):
        return "evidence_dump"
    if any(m.lower() in resp_lower for m in _GENERIC_FALLBACK_MARKERS):
        return "generic_quality_fallback"
    if any(m.lower() in resp_lower for m in _WRONG_TOOL_MARKERS):
        return "wrong_tool"

    # Follow-up questions that hit wrong path
    followup_triggers = ["what was task", "what was option", "let's do", "lets do",
                         "do number", "and what does that mean", "what does that mean",
                         "simplify", "explain your recommendation"]
    if any(t in msg_lower for t in followup_triggers):
        return "lost_context"

    # Scout should have been dispatched
    scout_triggers = ["can your scouts", "can hermes find", "figure it out", "don't know"]
    if any(t in msg_lower for t in scout_triggers) and "i don't have verified" not in resp_lower:
        return "did_not_assign_scout"

    # Prompt should have been generated
    prompt_triggers = ["create a prompt", "give me a prompt", "prompt for claude", "super prompt"]
    if any(t in msg_lower for t in prompt_triggers) and "implementation prompt" not in resp_lower:
        return "did_not_create_prompt"

    if len(response) > 800:
        return "too_technical"

    return "generic_quality_fallback"


# ── Logging ───────────────────────────────────────────────────────────────────

def log_failed_response(
    message: str,
    response: str,
    reason: Optional[str] = None,
) -> dict:
    """Log a failed Hermes response for later training review."""
    failure_type = reason or classify_failure_type(message, response)
    entry = {
        "failure_id": f"fail_{_now_ts()}",
        "failure_type": failure_type,
        "user_message": message[:400],
        "bad_response_summary": response[:300],
        "reason": failure_type,
        "created_at": _now_iso(),
        "reviewed": False,
    }
    try:
        _TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        with _FAILED_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("log_failed_response error: %s", exc)
    return entry


def suggest_training_example(message: str, response: str) -> dict:
    """Generate a training suggestion from a bad message/response pair."""
    failure_type = classify_failure_type(message, response)

    # Build the ideal response description
    ideal_desc = _ideal_response_for(failure_type, message)

    suggestion = {
        "suggestion_id": f"train_{_now_ts()}",
        "user_message": message[:400],
        "bad_response_summary": response[:200],
        "failure_type": failure_type,
        "ideal_response_description": ideal_desc,
        "created_at": _now_iso(),
    }
    try:
        _TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        with _TRAINING_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(suggestion) + "\n")
    except Exception as exc:
        logger.warning("suggest_training_example error: %s", exc)
    return suggestion


def _ideal_response_for(failure_type: str, message: str) -> str:
    """Return a description of the ideal response for a failure type."""
    templates = {
        "evidence_dump": (
            "Start with PLAIN ANSWER. Answer the question in 2-3 sentences. "
            "No artifact inventory. No evidence section."
        ),
        "generic_quality_fallback": (
            "Use the CFO brain to understand the real intent. "
            "Route to the correct handler. Respond with plain language."
        ),
        "wrong_tool": (
            f"The message '{message[:80]}' needed a different tool. "
            "Match intent to the correct Hermes tool."
        ),
        "lost_context": (
            "Load conversation state. Resolve the reference (task 1, option 1, etc.) "
            "from last_task_map / last_option_map. Answer directly."
        ),
        "failed_followup": (
            "Use handle_followup_question() with conversation context. "
            "Do not start fresh — thread the prior conversation."
        ),
        "too_technical": (
            "Use simplify_response_text() to shorten the response. "
            "Lead with the plain answer, then offer details on request."
        ),
        "did_not_assign_scout": (
            "If Hermes cannot answer confidently, call scout dispatch. "
            "Respond with: I DON'T HAVE VERIFIED EVIDENCE YET"
        ),
        "did_not_create_prompt": (
            "Detect the prompt generation request and call "
            "_build_implementation_prompt_text(). Return IMPLEMENTATION PROMPT."
        ),
    }
    return templates.get(failure_type, "Respond with PLAIN ANSWER in 2-3 sentences. No evidence dump.")


def generate_test_from_failure(example: dict) -> dict:
    """Generate a test case spec from a failure example."""
    return {
        "test_id": f"test_{_now_ts()}",
        "input_message": example.get("user_message", ""),
        "expected_response_starts_with": _expected_header_for(example.get("failure_type", "")),
        "must_not_contain": _must_not_contain_for(example.get("failure_type", "")),
        "failure_type": example.get("failure_type", ""),
        "source_failure_id": example.get("failure_id", ""),
        "created_at": _now_iso(),
    }


def _expected_header_for(failure_type: str) -> str:
    return {
        "evidence_dump": "PLAIN ANSWER",
        "generic_quality_fallback": "PLAIN ANSWER",
        "lost_context": "PLAIN ANSWER",
        "failed_followup": "PLAIN ANSWER",
        "did_not_assign_scout": "I DON'T HAVE VERIFIED",
        "did_not_create_prompt": "IMPLEMENTATION PROMPT",
        "wrong_tool": "PLAIN ANSWER",
        "too_technical": "PLAIN ANSWER",
    }.get(failure_type, "PLAIN ANSWER")


def _must_not_contain_for(failure_type: str) -> list[str]:
    return {
        "evidence_dump": ["artifact_inventory", "handoff", "════", "Evidence:"],
        "generic_quality_fallback": ["quality response", "i wasn't sure", "plain language mode"],
        "lost_context": ["I wasn't sure what you meant", "quality fallback"],
    }.get(failure_type, ["i wasn't sure what you meant"])


# ── Review commands ───────────────────────────────────────────────────────────

def format_failure_review() -> str:
    """Format failed responses for Ray review."""
    try:
        if not _FAILED_PATH.exists():
            return "FAILED RESPONSES\n\nNo failed responses logged yet."
        lines = _FAILED_PATH.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    e = json.loads(line)
                    if not e.get("reviewed"):
                        entries.append(e)
                except json.JSONDecodeError:
                    pass
        if not entries:
            return "FAILED RESPONSES\n\nNo unreviewed failures on file."
        result = ["FAILED RESPONSES", "", f"{len(entries)} unreviewed failures:", ""]
        for e in entries[-10:]:
            result += [
                f"  [{e.get('failure_type', '?')}] {e.get('user_message', '?')[:60]}",
                f"    Bad response: {e.get('bad_response_summary', '')[:80]}",
                f"    Logged: {e.get('created_at', '')[:19]}",
                "",
            ]
        return "\n".join(result)
    except Exception as exc:
        return f"FAILED RESPONSES\n\nCould not load: {exc!s:.100}"


def load_failed_responses(reviewed: Optional[bool] = False) -> list[dict]:
    """Load failed response entries."""
    try:
        if not _FAILED_PATH.exists():
            return []
        entries = []
        for line in _FAILED_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    e = json.loads(line)
                    if reviewed is None or e.get("reviewed") == reviewed:
                        entries.append(e)
                except json.JSONDecodeError:
                    pass
        return entries
    except Exception:
        return []
