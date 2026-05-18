"""
hermes_response_patterns.py — Load and match Hermes conversational response patterns.

Loads approved patterns from Supabase (hermes_response_patterns table) with
in-memory cache. Falls back to embedded defaults if Supabase is unavailable.

Called by hermes_internal_first.py as the first intercept layer for
conversational/greeting messages that don't match operational keywords.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("HermesResponsePatterns")

_CACHE: list[dict[str, Any]] | None = None
_CACHE_EXPIRES: float = 0.0
_CACHE_TTL = 300  # 5 min


# ── Embedded defaults (used if Supabase unavailable) ─────────────────────────

_DEFAULT_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern_key": "greeting_good_morning",
        "trigger_examples": ["good morning", "morning hermes", "morning", "hey hermes", "hi hermes", "hello hermes", "gm"],
        "intent": "morning_greeting",
        "desired_tone": "operational_warm_brief",
        "response_template": "Morning, Ray. Nexus is running — watching roadmap, providers, and task queue. {operational_context}",
        "next_action_rule": "check_operational_context_then_next_best_action",
        "priority": 10,
    },
    {
        "pattern_key": "greeting_how_are_you",
        "trigger_examples": ["how are you", "how's it going", "how are things", "what's up", "sup", "how you doing"],
        "intent": "status_check_personal",
        "desired_tone": "operational_conversational",
        "response_template": "Solid, Ray — I'm tracking operations. {brief_status} What do you need?",
        "next_action_rule": "summarize_brief_operational_state",
        "priority": 15,
    },
    {
        "pattern_key": "task_completion_ack",
        "trigger_examples": ["done", "finished", "completed", "all done", "wrapped up", "just finished", "just completed"],
        "intent": "completion_acknowledgement",
        "desired_tone": "brief_affirming",
        "response_template": "Noted and logged. {context_note} Ready for the next one — check 'show roadmap' for priorities.",
        "next_action_rule": "check_roadmap_for_next_task",
        "priority": 30,
    },
    {
        "pattern_key": "blocker_detected",
        "trigger_examples": ["blocked", "stuck", "can't proceed", "hitting a wall", "something's broken"],
        "intent": "blocker_triage",
        "desired_tone": "calm_problem_solving",
        "response_template": "Got it — what's blocked specifically? Tell me and I'll check if Nexus has context or if we need to escalate.",
        "escalation_rule": "create_blocker_ticket_if_unresolved",
        "next_action_rule": "diagnose_and_route",
        "priority": 25,
    },
]


def _load_from_supabase() -> list[dict[str, Any]] | None:
    """Try to load patterns from Supabase. Returns None on any failure."""
    try:
        from scripts.prelaunch_utils import rest_select
        rows = rest_select("hermes_response_patterns?enabled=eq.true&status=eq.approved&order=priority.asc") or []
        if isinstance(rows, list) and rows:
            return rows
    except Exception as exc:
        logger.debug("hermes_response_patterns: Supabase load failed: %s", exc)
    return None


def get_patterns(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Return response patterns, using cache, Supabase, or embedded defaults."""
    global _CACHE, _CACHE_EXPIRES
    now = time.time()
    if not force_refresh and _CACHE is not None and now < _CACHE_EXPIRES:
        return _CACHE
    fresh = _load_from_supabase()
    if fresh:
        _CACHE = fresh
        _CACHE_EXPIRES = now + _CACHE_TTL
        return fresh
    # Fall back to embedded defaults
    if _CACHE is None:
        _CACHE = _DEFAULT_PATTERNS
        _CACHE_EXPIRES = now + 60  # retry Supabase sooner for defaults
    return _CACHE


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def match_pattern(text: str) -> dict[str, Any] | None:
    """
    Find the best matching response pattern for incoming text.

    Returns the pattern dict if matched, else None.
    Matching: any trigger_example phrase is a substring of normalized text.
    Priority: lower number = higher priority.
    """
    t = _normalize(text)
    if not t:
        return None
    patterns = get_patterns()
    matched: list[tuple[int, dict[str, Any]]] = []
    for p in patterns:
        if not p.get("enabled", True):
            continue
        triggers = p.get("trigger_examples") or []
        if any(_normalize(trig) in t for trig in triggers if trig):
            priority = int(p.get("priority") or 100)
            matched.append((priority, p))
    if not matched:
        return None
    matched.sort(key=lambda x: x[0])
    return matched[0][1]


def fill_template(template: str, context: dict[str, str]) -> str:
    """Substitute {placeholders} in template with context values."""
    result = template
    for key, val in context.items():
        result = result.replace("{" + key + "}", str(val))
    # Remove unfilled placeholders gracefully
    import re
    result = re.sub(r'\{[a-z_]+\}', '', result).strip()
    # Clean up double spaces
    result = re.sub(r'  +', ' ', result)
    return result
