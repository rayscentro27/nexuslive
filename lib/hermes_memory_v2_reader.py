"""
hermes_memory_v2_reader.py — Preview-only reader for hermes_memory_v2.

Reads structured memory from hermes_memory_v2 in READ-ONLY preview mode.
The live Telegram reader has NOT been switched to v2. This module is for:
  - Preview and comparison tooling
  - Batch 2 dry-run preparation
  - Operator-facing 'show memory v2 preview' commands

Rules enforced:
  1. Only reads status='active' AND scope='live_answer' records.
  2. Excludes: blocked, deprecated, archived, historical, debug, needs_review.
  3. Never returns payload secrets or raw sensitive fields.
  4. Never uses provider_status_snapshot as current truth (this phase).
  5. Never uses executive_briefings as current truth (this phase).
  6. Reader is preview-only — does not affect live Telegram answers.
  7. Live Telegram reader is NOT switched to v2 in this phase.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("HermesMemoryV2Reader")

_SUPABASE_WRITE_ATTEMPTED = False  # sentinel — must remain False at all times

# Safe columns to return — never includes payload, summary (raw), or internal fields
_SAFE_COLUMNS = "memory_id,title,memory_type,status,scope,priority,confidence,tags,updated_at"

# Types excluded from current-truth in preview phase
_EXCLUDED_FROM_CURRENT_TRUTH = frozenset({
    "provider_status_snapshot",
    "executive_briefings",
    "fallback_rule",
    "debug_note",
    "archived_note",
    "template",
})

# Only these statuses/scopes are valid for live-answer preview
_VALID_STATUS = "active"
_VALID_SCOPE = "live_answer"

_STALE_MARKERS = [
    "Ollama OFFLINE", "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "Executive Memory — as of",
    "Quality escalation fallback", "NitroTrades",
]


def _supabase_env() -> tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return url, key


def _env_available() -> bool:
    url, key = _supabase_env()
    return bool(url and key)


def _v2_unavailable(reason: str = "credentials not configured") -> dict:
    return {
        "available": False,
        "reason": f"v2 reader unavailable — {reason}",
        "records": [],
        "count": 0,
    }


def _has_stale(text: str) -> bool:
    lower = (text or "").lower()
    return any(m.lower() in lower for m in _STALE_MARKERS)


def _safe_row(row: dict) -> dict:
    """Strip raw payload and internal fields — return only safe display fields."""
    return {
        "memory_id": row.get("memory_id", ""),
        "title":     row.get("title", ""),
        "memory_type": row.get("memory_type", ""),
        "status":    row.get("status", ""),
        "scope":     row.get("scope", ""),
        "priority":  row.get("priority"),
        "confidence": row.get("confidence"),
        "tags":      row.get("tags", []),
        "updated_at": row.get("updated_at", ""),
    }


def _query(memory_type: str | None = None, limit: int = 50) -> list[dict]:
    """Internal query — always filters status=active AND scope=live_answer."""
    assert _SUPABASE_WRITE_ATTEMPTED is False, "write sentinel violated"
    url, key = _supabase_env()
    if not url or not key:
        return []
    try:
        from supabase import create_client
        client = create_client(url, key)
        q = (
            client.table("hermes_memory_v2")
            .select(_SAFE_COLUMNS)
            .eq("status", _VALID_STATUS)
            .eq("scope", _VALID_SCOPE)
            .order("priority", desc=True)
            .limit(limit)
        )
        if memory_type:
            q = q.eq("memory_type", memory_type)
        resp = q.execute()
        rows = resp.data or []
        # Extra safety: filter out excluded types
        rows = [r for r in rows if r.get("memory_type") not in _EXCLUDED_FROM_CURRENT_TRUTH]
        # Filter out stale markers
        rows = [r for r in rows if not _has_stale(r.get("title", "") + r.get("memory_type", ""))]
        return [_safe_row(r) for r in rows]
    except Exception as exc:
        logger.debug("hermes_memory_v2 query failed: %s", exc)
        return []


def _count_by_type(memory_type: str) -> int:
    """Return count of active/live_answer records for a given type."""
    url, key = _supabase_env()
    if not url or not key:
        return 0
    try:
        from supabase import create_client
        client = create_client(url, key)
        resp = (
            client.table("hermes_memory_v2")
            .select("memory_id", count="exact")
            .eq("status", _VALID_STATUS)
            .eq("scope", _VALID_SCOPE)
            .eq("memory_type", memory_type)
            .execute()
        )
        return resp.count if resp.count is not None else len(resp.data or [])
    except Exception:
        return 0


def _total_count() -> int:
    """Return total active/live_answer count."""
    url, key = _supabase_env()
    if not url or not key:
        return 0
    try:
        from supabase import create_client
        client = create_client(url, key)
        resp = (
            client.table("hermes_memory_v2")
            .select("memory_id", count="exact")
            .eq("status", _VALID_STATUS)
            .eq("scope", _VALID_SCOPE)
            .execute()
        )
        return resp.count if resp.count is not None else len(resp.data or [])
    except Exception:
        return 0


# ── Public reader functions ────────────────────────────────────────────────────

def load_v2_active_live_answer_memory(limit: int = 50) -> dict:
    """Load all active/live_answer records from hermes_memory_v2.

    Returns dict with 'available', 'count', 'records', 'reason'.
    Never crashes; returns unavailable dict on any error.
    """
    if not _env_available():
        return _v2_unavailable("credentials not configured")
    try:
        records = _query(limit=limit)
        return {"available": True, "count": len(records), "records": records, "reason": ""}
    except Exception as exc:
        return _v2_unavailable(str(exc)[:120])


def load_v2_operating_rules(limit: int = 20) -> dict:
    """Load operating_rule records from hermes_memory_v2."""
    if not _env_available():
        return _v2_unavailable()
    try:
        records = _query(memory_type="operating_rule", limit=limit)
        return {"available": True, "count": len(records), "records": records, "reason": ""}
    except Exception as exc:
        return _v2_unavailable(str(exc)[:120])


def load_v2_ray_preferences(limit: int = 20) -> dict:
    """Load ray_preference records from hermes_memory_v2."""
    if not _env_available():
        return _v2_unavailable()
    try:
        records = _query(memory_type="ray_preference", limit=limit)
        return {"available": True, "count": len(records), "records": records, "reason": ""}
    except Exception as exc:
        return _v2_unavailable(str(exc)[:120])


def load_v2_approval_policies(limit: int = 20) -> dict:
    """Load approval_policy records from hermes_memory_v2."""
    if not _env_available():
        return _v2_unavailable()
    try:
        records = _query(memory_type="approval_policy", limit=limit)
        return {"available": True, "count": len(records), "records": records, "reason": ""}
    except Exception as exc:
        return _v2_unavailable(str(exc)[:120])


def load_v2_project_context(limit: int = 20) -> dict:
    """Load project_context records from hermes_memory_v2."""
    if not _env_available():
        return _v2_unavailable()
    try:
        records = _query(memory_type="project_context", limit=limit)
        return {"available": True, "count": len(records), "records": records, "reason": ""}
    except Exception as exc:
        return _v2_unavailable(str(exc)[:120])


def load_v2_memory_by_type(memory_type: str, limit: int = 20) -> dict:
    """Load records of a specific memory_type from hermes_memory_v2."""
    if memory_type in _EXCLUDED_FROM_CURRENT_TRUTH:
        return _v2_unavailable(
            f"{memory_type!r} excluded from current-truth preview (phase restriction)"
        )
    if not _env_available():
        return _v2_unavailable()
    try:
        records = _query(memory_type=memory_type, limit=limit)
        return {"available": True, "count": len(records), "records": records, "reason": ""}
    except Exception as exc:
        return _v2_unavailable(str(exc)[:120])


def build_v2_memory_context_pack(limit: int = 50) -> dict:
    """Build a structured context pack from all active/live_answer v2 records.

    Groups records by memory_type with counts. Returns safe display fields only.
    Never returns payload. Preview-only.
    """
    if not _env_available():
        return {
            "available": False,
            "reason": "v2 reader unavailable — credentials not configured",
            "total": 0,
            "by_type": {},
            "records": [],
        }
    try:
        records = _query(limit=limit)
        by_type: dict[str, list[dict]] = {}
        for r in records:
            mt = r.get("memory_type", "unknown")
            by_type.setdefault(mt, []).append(r)
        return {
            "available": True,
            "reason": "",
            "total": len(records),
            "by_type": {mt: len(recs) for mt, recs in by_type.items()},
            "records": records,
        }
    except Exception as exc:
        return {
            "available": False,
            "reason": f"query failed: {str(exc)[:120]}",
            "total": 0,
            "by_type": {},
            "records": [],
        }


def compare_v2_with_current_memory() -> dict:
    """Compare hermes_memory_v2 preview with current active memory sources.

    Returns a comparison dict describing overlap, gaps, and recommendation.
    Does NOT switch readers. Does NOT write.
    """
    from lib.hermes_active_memory_reader import (
        load_active_operating_rules,
        load_active_goals,
        active_memory_available,
        CATEGORIES,
    )

    current_available = active_memory_available()
    current_sources = [
        "Current conversation context",
        "Latest content artifacts",
        "Action queue",
        "Decision log",
        "Source intake records",
        "Active operating rules (hermes_executive_memory)",
    ]

    v2_pack = build_v2_memory_context_pack(limit=50)
    v2_available = v2_pack.get("available", False)
    v2_total = v2_pack.get("total", 0)
    v2_by_type = v2_pack.get("by_type", {})

    # Overlap: types in v2 that correspond to current reader capabilities
    type_to_current = {
        "operating_rule":   "Active operating rules",
        "ray_preference":   "Ray preferences (implicit in conversation)",
        "approval_policy":  "Approval policies (implicit in routing)",
        "project_context":  "Project context (artifact/action queue)",
    }
    overlap = [
        f"v2 {mt} ({cnt} records) → {type_to_current[mt]}"
        for mt, cnt in v2_by_type.items()
        if mt in type_to_current and cnt > 0
    ]
    extra_in_v2 = [
        f"{mt} ({cnt} records)"
        for mt, cnt in v2_by_type.items()
        if mt not in type_to_current and cnt > 0
    ]

    # Batch 2 types — present only after Batch 2 is applied
    batch2_types = {"lesson", "goal", "tool_registry", "scout_registry"}
    missing_from_v2 = sorted(t for t in batch2_types if v2_by_type.get(t, 0) == 0)

    if missing_from_v2:
        recommendation = (
            "Keep v2 in preview/shadow mode until missing types are backfilled."
            " Switch to v2 as primary only after Ray approval."
        )
    else:
        recommendation = (
            "Batch 2 applied — all lesson/goal/tool_registry/scout_registry types present in v2."
            " Memory v2 is ready for shadow-reader testing, but not primary live Telegram yet."
            " Enable shadow mode with HERMES_MEMORY_V2_MODE=shadow. Primary requires Ray approval."
        )

    return {
        "current_available": current_available,
        "current_sources": current_sources,
        "v2_available": v2_available,
        "v2_total": v2_total,
        "v2_by_type": v2_by_type,
        "overlap": overlap,
        "extra_in_v2": extra_in_v2,
        "missing_from_v2": missing_from_v2,
        "recommendation": recommendation,
    }


def explain_v2_reader_status() -> str:
    """Plain-language status of the v2 reader — for 'show memory v2 status'."""
    if not _env_available():
        return (
            "HERMES MEMORY V2 STATUS\n\n"
            "Status: preview reader unavailable — Supabase credentials not configured in this environment.\n\n"
            "The v2 reader module is loaded but cannot connect to Supabase.\n"
            "Live Telegram reader has NOT been switched to v2."
        )
    total = _total_count()
    all_types = [
        "operating_rule", "ray_preference", "approval_policy", "project_context",
        "lesson", "goal", "tool_registry", "scout_registry",
    ]
    counts = {mt: _count_by_type(mt) for mt in all_types}

    lines = [
        "HERMES MEMORY V2 STATUS",
        "",
        "Mode: preview only — not the live Telegram primary reader",
        "",
        f"Active/live_answer records: {total}",
    ]
    for mt, cnt in counts.items():
        if cnt > 0:
            lines.append(f"  {mt}: {cnt}")
    lines += [
        "",
        "Excluded from current-truth preview:",
        "  provider_status_snapshot, executive_briefings, fallback_rule,",
        "  debug_note, archived_note, template",
        "",
        "Live Telegram reader: NOT switched to v2 (preview only)",
        "Preview command: 'show memory v2 preview'",
        "",
        "Evidence:",
        "- hermes_memory_v2 (Supabase table)",
        "- docs/HERMES_MEMORY_SAFETY_CONTRACT.md",
    ]
    return "\n".join(lines)
