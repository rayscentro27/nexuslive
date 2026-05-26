"""
Hermes Response Quality Guard
================================
Detects and escalates low-quality, generic, or filler responses before they
reach the user. Three detection modes:

  GENERIC    — boilerplate phrases, non-operational filler
  REPETITIVE — near-duplicate of a prior reply in this session
  NON_ACTIONABLE — no data, no next step, no decision support

When a response is flagged, the guard escalates by:
  1. Retry with enriched context (executive memory + stricter prompt)
  2. Route to a higher-reasoning provider (openrouter → reason tier)
  3. Return a structured apology + raw data block instead of filler

Usage:
  from lib.hermes_response_quality import quality_check, escalate
  result = quality_check(text, chat_id="tg_12345")
  if result.flagged:
      better = escalate(user_msg, context, result.reason)
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("HermesResponseQuality")

# ── Generic filler patterns ───────────────────────────────────────────────────

_FILLER_PHRASES: frozenset[str] = frozenset({
    "i'm here to help",
    "how can i assist you",
    "as an ai",
    "as a large language model",
    "i don't have access to real-time",
    "i cannot provide financial advice",
    "please consult a professional",
    "i'm just an ai",
    "as your assistant",
    "let me know if you need anything else",
    "feel free to ask",
    "i hope this helps",
    "in conclusion",
    "to summarize",
    "certainly!",
    "absolutely!",
    "great question",
    "that's a great question",
    "i understand your concern",
    "thank you for asking",
    "of course!",
    "sure thing",
    "i'd be happy to help",
    "i'm unable to",
    "unfortunately, i",
    "i apologize, but",
    "i must clarify",
})

_FILLER_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(certainly|absolutely|of course|sure thing)\b[\s!,.]", re.I),
    re.compile(r"\bas (an? )?(ai|language model|assistant|chatbot)\b", re.I),
    re.compile(r"\bi('m| am) (unable|not able|cannot) to\b", re.I),
    re.compile(r"\bfeel free to (ask|reach out)\b", re.I),
    re.compile(r"\blet me know if (you|there is)\b", re.I),
    re.compile(r"\bi hope (this |that )?(helps|is useful|answers)\b", re.I),
    re.compile(r"\bgreat question\b", re.I),
    re.compile(r"\bthank you for (asking|bringing|sharing)\b", re.I),
    re.compile(r"\bi don.t have (access to|real.?time)\b", re.I),
    re.compile(r"\bplease (consult|seek|speak to) (a |an )?(professional|expert|financial)\b", re.I),
]

# Operational indicators — these redeem a response
_OPERATIONAL_SIGNALS: list[re.Pattern] = [
    re.compile(r"\d+[\s/]\d+"),            # numeric ratio (3/11, 5/5)
    re.compile(r"supabase|postgres", re.I),
    re.compile(r"\$\d+|\d+%"),             # money or percentage
    re.compile(r"`[a-z_]+`"),              # code reference
    re.compile(r"nexus|hermes|oracle|worker", re.I),
    re.compile(r"(error|failed|offline|blocked)", re.I),
    re.compile(r"(quota|pipeline|briefing|affiliate|content)", re.I),
    re.compile(r"\b(run|check|execute|deploy|push|seed|audit)\b", re.I),
]

_MIN_OPERATIONAL_SIGNALS = 2


# ── Session dedup cache ───────────────────────────────────────────────────────

_SESSION_HASHES: dict[str, deque] = {}
_SESSION_TTL = 1800  # 30 min

def _response_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.lower().strip())[:500]
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def _register_response(chat_id: str, text: str) -> None:
    if chat_id not in _SESSION_HASHES:
        _SESSION_HASHES[chat_id] = deque(maxlen=10)
    _SESSION_HASHES[chat_id].append({
        "hash": _response_hash(text),
        "ts": time.monotonic(),
    })


def _is_duplicate(chat_id: str, text: str) -> bool:
    h = _response_hash(text)
    entries = _SESSION_HASHES.get(chat_id, [])
    cutoff = time.monotonic() - _SESSION_TTL
    return any(e["hash"] == h and e["ts"] > cutoff for e in entries)


# ── Quality check result ──────────────────────────────────────────────────────

@dataclass
class QualityResult:
    flagged: bool = False
    reason: str = ""
    filler_count: int = 0
    operational_signal_count: int = 0
    is_duplicate: bool = False
    score: float = 1.0  # 0.0 = terrible, 1.0 = great


def quality_check(text: str, chat_id: str = "") -> QualityResult:
    """Score a response for quality. Register it in session dedup cache."""
    if not text or len(text) < 10:
        return QualityResult(flagged=True, reason="empty_response", score=0.0)

    result = QualityResult()

    # Duplicate check
    if chat_id and _is_duplicate(chat_id, text):
        result.is_duplicate = True
        result.flagged = True
        result.reason = "duplicate_response"
        result.score = 0.1
        return result

    text_lower = text.lower()

    # Count filler phrases
    filler_hits = sum(1 for phrase in _FILLER_PHRASES if phrase in text_lower)
    filler_hits += sum(1 for pattern in _FILLER_PATTERNS if pattern.search(text))
    result.filler_count = filler_hits

    # Count operational signals (redeeming content)
    ops_signals = sum(1 for pattern in _OPERATIONAL_SIGNALS if pattern.search(text))
    result.operational_signal_count = ops_signals

    # Scoring
    filler_penalty = min(filler_hits * 0.15, 0.6)
    ops_bonus = min(ops_signals * 0.1, 0.4)
    result.score = max(0.0, min(1.0, 1.0 - filler_penalty + ops_bonus))

    # Flag if too generic and not redeemed by operational content
    if filler_hits >= 2 and ops_signals < _MIN_OPERATIONAL_SIGNALS:
        result.flagged = True
        result.reason = f"generic_filler (filler={filler_hits}, ops_signals={ops_signals})"
    elif filler_hits >= 4:
        result.flagged = True
        result.reason = f"high_filler (filler={filler_hits})"

    # Register in dedup cache
    if chat_id:
        _register_response(chat_id, text)

    return result


# ── Escalation ────────────────────────────────────────────────────────────────

def build_escalation_prompt(
    user_message: str,
    prior_response: str,
    quality_result: QualityResult,
    executive_context: str = "",
) -> str:
    """Build an enriched retry prompt that forces operational specificity."""
    return f"""You are Hermes, the executive intelligence system for Nexus AI.

PROBLEM: Your previous response was flagged as low quality.
Reason: {quality_result.reason}
Prior response excerpt: {prior_response[:200]}...

REQUIREMENT: Respond with OPERATIONAL SPECIFICITY only.
- Reference actual system state (workers, quotas, errors, priorities)
- Give at minimum ONE concrete next action with a command or decision
- Do NOT use filler phrases, pleasantries, or generic AI disclaimers
- If you lack live data, state exactly which data is missing and how to get it

OPERATIONAL CONTEXT:
{executive_context or '(not available)'}

USER MESSAGE: {user_message}

Respond concisely, directly, and operationally:"""


def escalate(
    user_message: str,
    quality_result: QualityResult,
    chat_id: str = "",
    timeout: int = 30,
) -> str:
    """Attempt escalated retry with enriched context and higher-reasoning provider."""
    try:
        from lib.hermes_executive_memory import build_context_block
        exec_context = build_context_block(max_items_per_category=3)
    except Exception:
        exec_context = ""

    prompt = build_escalation_prompt(
        user_message=user_message,
        prior_response="",
        quality_result=quality_result,
        executive_context=exec_context,
    )

    # Try reason/planning tier providers
    try:
        from lib.model_router import call_with_routing
        reply = call_with_routing(
            task_type="reason",
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )
        if reply and len(reply) > 20:
            result = quality_check(reply, chat_id=chat_id)
            if not result.flagged:
                return reply
    except Exception as exc:
        logger.debug("Escalation routing failed: %s", exc)

    # Last resort: structured data block
    return _fallback_data_block(user_message, exec_context)


def _fallback_data_block(user_message: str, exec_context: str) -> str:
    """Return a structured data block when all LLM attempts fail."""
    return (
        f"[Quality escalation fallback — LLM response was too generic]\n\n"
        f"Your question: {user_message[:200]}\n\n"
        f"Current operational state:\n{exec_context[:800] if exec_context else '(unavailable)'}\n\n"
        f"Run `nexus ceo briefing` for the full executive briefing."
    )


# ── Stats ─────────────────────────────────────────────────────────────────────

_flag_counts: dict[str, int] = {}


def record_flag(reason: str) -> None:
    _flag_counts[reason] = _flag_counts.get(reason, 0) + 1


def quality_stats() -> dict[str, Any]:
    return {"flag_counts": dict(_flag_counts), "session_count": len(_SESSION_HASHES)}
