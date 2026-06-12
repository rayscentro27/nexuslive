"""
hermes_conversational_router.py
Routes broad natural-language messages to existing Hermes handlers
or safe plain-language responses before any LLM/fallback path.

Routing priority (within conversational path):
  1. small_talk           → static response
  2. capability_question  → static capability list
  3. memory_source        → delegate to memory command handler
  4. system_health        → run_command health check
  5. monetization         → run_command opportunities
  6. external_info        → unavailable message + log gap
  7. content_asset        → redirect to content commands
  8. unknown              → log gap + safe fallback
"""
from __future__ import annotations

import logging
import re

from lib.hermes_language_pack import (
    SMALL_TALK_PHRASES, SMALL_TALK_RESPONSE,
    CAPABILITY_PHRASES, CAPABILITY_RESPONSE,
    SYSTEM_HEALTH_PHRASES, SYSTEM_HEALTH_COMMAND,
    MONETIZATION_PHRASES, MONETIZATION_COMMAND,
    CONTENT_ASSET_PHRASES, CONTENT_ASSET_REDIRECT,
    MEMORY_SOURCE_PHRASES,
    is_external_info, external_info_topic, format_external_unavailable_response,
    UNKNOWN_FALLBACK_RESPONSE,
    CATEGORY_SMALL_TALK, CATEGORY_CAPABILITY, CATEGORY_SYSTEM_HEALTH,
    CATEGORY_MONETIZATION, CATEGORY_CONTENT_ASSET, CATEGORY_MEMORY_SOURCE,
    CATEGORY_EXTERNAL_INFO, CATEGORY_UNKNOWN,
    GAP_UNSUPPORTED_EXTERNAL, GAP_MISSING_ROUTE, GAP_MISSING_ACTIVE_MEMORY,
)

logger = logging.getLogger(__name__)

# ── Normalisation ──────────────────────────────────────────────────────────────

def normalize_user_message(text: str) -> str:
    """Lowercase, collapse whitespace, strip trailing punctuation."""
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = t.rstrip("?!.,;:")
    return t


# ── Phrase checkers ────────────────────────────────────────────────────────────

def _phrase_match(text: str, phrases: frozenset[str]) -> bool:
    """True if text is exact match OR any phrase is a substring of text."""
    return text in phrases or any(p in text for p in phrases)


def is_small_talk(message: str) -> bool:
    return _phrase_match(normalize_user_message(message), SMALL_TALK_PHRASES)


def is_capability_question(message: str) -> bool:
    return _phrase_match(normalize_user_message(message), CAPABILITY_PHRASES)


def is_system_health_question(message: str) -> bool:
    return _phrase_match(normalize_user_message(message), SYSTEM_HEALTH_PHRASES)


def is_monetization_question(message: str) -> bool:
    return _phrase_match(normalize_user_message(message), MONETIZATION_PHRASES)


def is_content_asset_question(message: str) -> bool:
    return _phrase_match(normalize_user_message(message), CONTENT_ASSET_PHRASES)


def is_memory_source_question(message: str) -> bool:
    return _phrase_match(normalize_user_message(message), MEMORY_SOURCE_PHRASES)


def is_external_info_question(message: str) -> bool:
    return is_external_info(normalize_user_message(message))


# ── Intent classifier ─────────────────────────────────────────────────────────

def classify_conversational_intent(user_message: str) -> str:
    """Return the single best-fit category for a user message."""
    t = normalize_user_message(user_message)
    if is_small_talk(t):
        return CATEGORY_SMALL_TALK
    if is_capability_question(t):
        return CATEGORY_CAPABILITY
    if is_memory_source_question(t):
        return CATEGORY_MEMORY_SOURCE
    if is_system_health_question(t):
        return CATEGORY_SYSTEM_HEALTH
    if is_monetization_question(t):
        return CATEGORY_MONETIZATION
    if is_external_info_question(t):
        return CATEGORY_EXTERNAL_INFO
    if is_content_asset_question(t):
        return CATEGORY_CONTENT_ASSET
    return CATEGORY_UNKNOWN


# ── Static formatters ──────────────────────────────────────────────────────────

def format_capability_response() -> str:
    return CAPABILITY_RESPONSE


def format_external_unavailable(topic: str) -> str:
    return format_external_unavailable_response(topic)


def format_unknown_question_response(user_message: str) -> str:
    return UNKNOWN_FALLBACK_RESPONSE


# ── Main router ───────────────────────────────────────────────────────────────

def route_conversational_intent(user_message: str) -> str | None:
    """
    Classify and handle a user message.
    Returns a string response or None if the message should continue to the LLM path.

    Never returns stale executive memory, artifact dumps, or handoff dumps.
    Logs gaps for external info and unknown categories.
    """
    from lib.hermes_knowledge_gap_logger import log_knowledge_gap, format_gap_logged_response

    # ── 0. User-provided source + monetization intent → Monetization Scout ──
    #   If Ray pasted a transcript/article/notes AND asked a strategic/monetization
    #   question, treat the pasted content as PRIMARY evidence and return a Nexus-first
    #   revenue plan. Runs BEFORE any evidence/artifact/opportunities path so Hermes
    #   never falls into verified-artifact/evidence-dump mode on a supplied source.
    try:
        from lib.hermes_monetization_scout import should_handle as _scout_should_handle, run_scout
        if _scout_should_handle(user_message):
            logger.info("conversational_router route=monetization_scout (user-provided source)")
            return run_scout(user_message)
    except Exception:
        logger.exception("monetization_scout layer failed; continuing to normal routing")

    intent = classify_conversational_intent(user_message)
    logger.info("conversational_router intent=%s message=%r", intent, user_message[:60])

    # ── 1. Small talk — static response, no gap logged ────────────────────
    if intent == CATEGORY_SMALL_TALK:
        logger.info("conversational_router route=small_talk")
        return SMALL_TALK_RESPONSE

    # ── 2. Capability question — static response, no gap logged ──────────
    if intent == CATEGORY_CAPABILITY:
        logger.info("conversational_router route=capability")
        return format_capability_response()

    # ── 3. Memory source — inline static response (avoids dedup collision with
    #       _try_memory_command path which fires first in handle_inbound_message)
    if intent == CATEGORY_MEMORY_SOURCE:
        logger.info("conversational_router route=memory_source_inline")
        try:
            from hermes_command_router.router import _run_memory_sources
            from hermes_command_router.report import build as build_report
            status, evidence, rec = _run_memory_sources()
            return build_report(
                status=status,
                what_happened="Ran memory sources check.",
                evidence=evidence,
                recommendation=rec,
                action_needed="none",
                command="show memory sources",
            )
        except Exception:
            return (
                "HERMES MEMORY SOURCES\n\n"
                "Live answer sources:\n"
                "- Current conversation context\n"
                "- Latest content artifact\n"
                "- Action queue\n"
                "- Decision log\n"
                "- Source intake registry\n"
                "- Daily research review\n"
                "- Active operating rules\n"
                "- Live provider policy\n\n"
                "Historical sources (explicit request only):\n"
                "- archived executive memory\n"
                "- stale memory debug\n\n"
                "Blocked from live answers:\n"
                "- old Executive Memory defaults\n"
                "- stale provider status\n\n"
                "Evidence: docs/HERMES_MEMORY_SAFETY_CONTRACT.md"
            )

    # ── 4. System health — route to existing health handler ───────────────
    if intent == CATEGORY_SYSTEM_HEALTH:
        logger.info("conversational_router route=system_health")
        try:
            from hermes_command_router.router import run_command
            return run_command(SYSTEM_HEALTH_COMMAND, source="telegram")
        except Exception as e:
            log_knowledge_gap(user_message, intent, GAP_MISSING_ROUTE)
            return format_gap_logged_response(user_message, intent, GAP_MISSING_ROUTE)

    # ── 5. Monetization — route to opportunities handler ─────────────────
    if intent == CATEGORY_MONETIZATION:
        logger.info("conversational_router route=monetization")
        try:
            from hermes_command_router.router import run_command
            result = run_command(MONETIZATION_COMMAND, source="telegram")
            if "artifact_missing" in result or "No active business" in result:
                log_knowledge_gap(user_message, intent, GAP_MISSING_ACTIVE_MEMORY)
                return format_gap_logged_response(user_message, intent, GAP_MISSING_ACTIVE_MEMORY)
            return result
        except Exception:
            log_knowledge_gap(user_message, intent, GAP_MISSING_ACTIVE_MEMORY)
            return format_gap_logged_response(user_message, intent, GAP_MISSING_ACTIVE_MEMORY)

    # ── 6. External info — unavailable message + log gap ─────────────────
    if intent == CATEGORY_EXTERNAL_INFO:
        logger.info("conversational_router route=external_info_gap")
        topic = external_info_topic(user_message)
        log_knowledge_gap(user_message, intent, GAP_UNSUPPORTED_EXTERNAL)
        return format_external_unavailable(topic)

    # ── 7. Content asset — redirect to content commands ───────────────────
    if intent == CATEGORY_CONTENT_ASSET:
        logger.info("conversational_router route=content_asset_redirect")
        return CONTENT_ASSET_REDIRECT

    # ── 8. Unknown — log gap and return safe fallback ─────────────────────
    logger.info("conversational_router route=unknown gap_logged")
    log_knowledge_gap(user_message, CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
    return None   # Return None to let the LLM try first; gap is already logged
