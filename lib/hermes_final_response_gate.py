"""
hermes_final_response_gate.py
==============================
Inspect every outgoing Telegram message before it reaches the user.
Block or flag responses that contain unsupported operational claims.

Blocked claim patterns:
  - Specific approval counts  ("6 pending approvals", "3 items need approval")
  - Fabricated task names     ("NitroTrades", "Slide 12", specific commit hashes)
  - Invented deadlines        ("SBA deadline is July 15", "Hello Alice closes")
  - Fake YouTube counts       ("28 videos processed", "15 links ingested")
  - Specific pending numbers  ("4 tasks pending", "7 action items")
  - Invented dollar amounts   ("$50,000 grant", "$12k funding approved")

Safe patterns (always allowed):
  - "No verified data for that yet"
  - "Ask me to run a status check"
  - "Run: show source intake"
  - Evidence-only summaries from artifact registry

Policy:
  - GATE_ACTION="warn"  (default) — log and annotate but deliver the response
  - GATE_ACTION="block" — replace blocked responses with safe fallback
  - HERMES_FINAL_GATE_ENABLED="true" (default: true)
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

GATE_ENABLED = os.getenv("HERMES_FINAL_GATE_ENABLED", "true").strip().lower() != "false"
GATE_ACTION  = os.getenv("HERMES_FINAL_GATE_ACTION", "warn").strip().lower()  # "warn" | "block"

# ── Blocked patterns ──────────────────────────────────────────────────────────

_BLOCKED_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Specific approval counts
    (re.compile(r"\b\d+\s+pending\s+approval", re.IGNORECASE),
     "fabricated_approval_count"),

    (re.compile(r"\b\d+\s+(item|task|thing)s?\s+(?:that\s+)?(need|require|await)\s+approval", re.IGNORECASE),
     "fabricated_approval_count"),

    (re.compile(r"approval\s+count[:\s]+\d+", re.IGNORECASE),
     "fabricated_approval_count"),

    # Invented specific task names
    (re.compile(r"\bNitroTrades\b", re.IGNORECASE),
     "fabricated_task_name_nitrotrades"),

    (re.compile(r"\bSlide\s+\d+\b", re.IGNORECASE),
     "fabricated_slide_reference"),

    # Commit hash patterns (8+ hex chars)
    (re.compile(r"\b[0-9a-f]{8,40}\b"),
     "fabricated_commit_hash"),

    # Invented deadlines
    (re.compile(r"\bSBA\s+deadline\s+(is|was|will be)\b", re.IGNORECASE),
     "fabricated_sba_deadline"),

    (re.compile(r"\bHello\s+Alice\s+(closes|deadline|due|opens)\b", re.IGNORECASE),
     "fabricated_hello_alice_deadline"),

    # Invented YouTube/video counts paired with specific numbers
    (re.compile(r"\b\d{2,}\s+(video|link|youtube|source)s?\s+(processed|ingested|tracked|sent)", re.IGNORECASE),
     "fabricated_youtube_count"),

    # Specific dollar amounts in funding claims (not in evidence)
    (re.compile(r"\$[\d,]+k?\s+(grant|funded|approved|available)\b", re.IGNORECASE),
     "fabricated_dollar_amount"),
]

# Safe phrases that override blocked patterns
_SAFE_OVERRIDES: list[str] = [
    "no verified data",
    "ask me to run a status check",
    "run: show source intake",
    "run a status check",
    "i don't have a verified artifact",
    "evidence-only",
    "[verified_file]",
    "[verified_log]",
    "[verified_supabase]",
]


@dataclass
class GateResult:
    passed: bool
    blocked_reasons: list[str] = field(default_factory=list)
    original_text: str = ""
    safe_text: str = ""

    @property
    def was_modified(self) -> bool:
        return self.safe_text != self.original_text


def _is_safe_override(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _SAFE_OVERRIDES)


def _build_safe_replacement(original: str, reasons: list[str]) -> str:
    return (
        "I don't have verified evidence for that specific claim. "
        "Run a status check to get real data: try 'show source intake', 'nexus status', or /status."
    )


def inspect(text: str) -> GateResult:
    """
    Inspect an outgoing response for unsupported operational claims.

    Returns GateResult. If GATE_ACTION="block" and claims found,
    safe_text contains the replacement message.
    If GATE_ACTION="warn", safe_text == original_text (delivered as-is).
    """
    if not GATE_ENABLED or not text:
        return GateResult(passed=True, original_text=text, safe_text=text)

    if _is_safe_override(text):
        return GateResult(passed=True, original_text=text, safe_text=text)

    blocked_reasons: list[str] = []
    for pattern, reason in _BLOCKED_PATTERNS:
        if pattern.search(text):
            blocked_reasons.append(reason)

    if not blocked_reasons:
        return GateResult(passed=True, original_text=text, safe_text=text)

    logger.warning(
        "hermes_final_gate BLOCKED reasons=%s text_preview=%r",
        blocked_reasons, text[:120],
    )

    if GATE_ACTION == "block":
        safe = _build_safe_replacement(text, blocked_reasons)
        return GateResult(
            passed=False,
            blocked_reasons=blocked_reasons,
            original_text=text,
            safe_text=safe,
        )

    # warn mode — deliver original but log
    return GateResult(
        passed=False,
        blocked_reasons=blocked_reasons,
        original_text=text,
        safe_text=text,
    )


def gate(text: str) -> str:
    """
    Convenience wrapper. Returns safe text to deliver to the user.
    In warn mode: returns original text (but logs violations).
    In block mode: returns replacement text if violations found.
    """
    result = inspect(text)
    return result.safe_text
