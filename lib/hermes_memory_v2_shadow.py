"""
hermes_memory_v2_shadow.py
Phase 4E: Shadow reader mode for hermes_memory_v2.

Shadow mode loads v2 memory context alongside the current active reader,
logs a comparison, but NEVER changes the live Telegram response and NEVER
switches the primary reader.

Mode config via HERMES_MEMORY_V2_MODE env var:
  off      — do not load v2 at all
  preview  — only explicit preview commands read v2 (default)
  shadow   — v2 loads in background for comparison/logging only
  primary  — BLOCKED in this phase; requires explicit Ray approval later

_SUPABASE_WRITE_ATTEMPTED = False  — sentinel, must remain False at all times.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Safety sentinel ────────────────────────────────────────────────────────────
_SUPABASE_WRITE_ATTEMPTED = False  # MUST remain False — no writes in this module

# ── Mode constants ─────────────────────────────────────────────────────────────
MODE_OFF     = "off"
MODE_PREVIEW = "preview"
MODE_SHADOW  = "shadow"
MODE_PRIMARY = "primary"   # blocked in this phase

_VALID_MODES = {MODE_OFF, MODE_PREVIEW, MODE_SHADOW}   # primary excluded from valid set

# ── Planned Batch 1/2 type coverage ───────────────────────────────────────────
PLANNED_BATCH_TYPES: tuple[str, ...] = (
    "operating_rule", "ray_preference", "approval_policy", "project_context",
    "lesson", "goal", "tool_registry", "scout_registry",
)

# ── Types always excluded from current-truth reads ────────────────────────────
EXCLUDED_FROM_CURRENT_TRUTH: tuple[str, ...] = (
    "provider_status_snapshot", "executive_briefings",
    "ai_task_queue", "agent_dispatch_tasks",
    "fallback_rule", "debug_note", "archived_note",
    "template",
)

# ── Shadow log path ────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
SHADOW_LOG_DIR  = _ROOT / "docs" / "reports" / "memory" / "shadow"
SHADOW_LOG_PATH = SHADOW_LOG_DIR / "hermes_memory_v2_shadow_log.jsonl"

# ── In-memory cache of last shadow result (for status command) ─────────────────
_last_shadow_result: dict = {}
_shadow_lock = threading.Lock()


# ── Mode helpers ───────────────────────────────────────────────────────────────

def get_memory_v2_mode() -> str:
    """Return current HERMES_MEMORY_V2_MODE.

    Defaults to 'preview'. Blocks 'primary' — logs warning and falls back to
    'shadow' if someone accidentally sets it.
    """
    raw = os.environ.get("HERMES_MEMORY_V2_MODE", MODE_PREVIEW).strip().lower()
    if raw == MODE_PRIMARY:
        logger.warning(
            "HERMES_MEMORY_V2_MODE=primary is blocked in Phase 4E — "
            "falling back to shadow. Ray approval required for primary."
        )
        return MODE_SHADOW
    if raw not in _VALID_MODES:
        logger.warning(
            "HERMES_MEMORY_V2_MODE=%r is invalid — falling back to preview.", raw
        )
        return MODE_PREVIEW
    return raw


def is_shadow_mode_enabled() -> bool:
    """Return True if shadow mode is active."""
    return get_memory_v2_mode() == MODE_SHADOW


def is_primary_mode_requested() -> bool:
    """Return True if someone set the env var to 'primary' (which is blocked)."""
    return os.environ.get("HERMES_MEMORY_V2_MODE", "").strip().lower() == MODE_PRIMARY


# ── Shadow context builder ─────────────────────────────────────────────────────

def _build_v2_context() -> dict:
    """Load v2 memory context pack (read-only). Returns empty dict on any error."""
    try:
        from lib.hermes_memory_v2_reader import build_v2_memory_context_pack
        return build_v2_memory_context_pack(limit=50)
    except Exception as exc:
        logger.debug("shadow _build_v2_context error: %s", exc)
        return {}


# ── Comparison ─────────────────────────────────────────────────────────────────

def compare_shadow_contexts(current_context: dict, v2_context: dict) -> dict:
    """Compare current reader context with v2 context.

    Returns safe metadata only — no payloads, no secrets.
    """
    v2_available  = v2_context.get("available", False)
    v2_total      = v2_context.get("total", 0)
    v2_by_type    = v2_context.get("by_type", {})

    current_sources = current_context.get("sources", [
        "current_conversation_context",
        "latest_content_artifacts",
        "action_queue",
        "decision_log",
        "source_intake_records",
        "active_operating_rules",
    ])

    # Coverage check: which planned types are present in v2?
    present = [t for t in PLANNED_BATCH_TYPES if v2_by_type.get(t, 0) > 0]
    missing = [t for t in PLANNED_BATCH_TYPES if v2_by_type.get(t, 0) == 0]

    # Risk flags
    risk_flags: list[str] = []
    if not v2_available:
        risk_flags.append("v2_unavailable")
    if missing:
        risk_flags.append(f"planned_types_missing: {missing}")

    coverage_pct = round(len(present) / len(PLANNED_BATCH_TYPES) * 100) if PLANNED_BATCH_TYPES else 0

    if missing:
        recommendation = (
            f"v2 is missing planned types: {missing}. Keep in preview/shadow until resolved."
        )
    else:
        recommendation = (
            "Batch 1/2 coverage complete. v2 shadow mode active. "
            "Primary mode requires Ray approval."
        )

    return {
        "v2_available":        v2_available,
        "v2_total":            v2_total,
        "v2_by_type":          v2_by_type,
        "current_sources":     current_sources,
        "planned_types_count": len(PLANNED_BATCH_TYPES),
        "present_count":       len(present),
        "missing_types":       missing,
        "coverage_pct":        coverage_pct,
        "risk_flags":          risk_flags,
        "recommendation":      recommendation,
        "live_response_changed": False,
    }


# ── Shadow run ─────────────────────────────────────────────────────────────────

def run_shadow_memory_comparison(
    user_message: str,
    current_context: dict | None = None,
    current_response: str | None = None,
) -> dict:
    """Run a shadow comparison and log result.

    Does NOT change current_response.
    Does NOT call any LLM.
    Does NOT block or slow the Telegram response path.
    Returns the comparison result dict.
    """
    assert _SUPABASE_WRITE_ATTEMPTED is False

    ts = datetime.now(timezone.utc).isoformat()
    msg_hash = hashlib.sha256((user_message or "").encode()).hexdigest()[:16]

    v2_ctx = _build_v2_context()
    comparison = compare_shadow_contexts(current_context or {}, v2_ctx)

    result = {
        "timestamp":            ts,
        "message_hash":         msg_hash,
        "mode":                 get_memory_v2_mode(),
        "current_sources":      comparison["current_sources"],
        "v2_record_count":      comparison["v2_total"],
        "v2_types":             comparison["v2_by_type"],
        "overlap_summary":      f"{comparison['present_count']}/{comparison['planned_types_count']} planned types present",
        "missing_summary":      comparison["missing_types"] or "none",
        "coverage_pct":         comparison["coverage_pct"],
        "risk_flags":           comparison["risk_flags"],
        "recommendation":       comparison["recommendation"],
        "live_response_changed": False,
    }

    log_shadow_memory_result(result)

    with _shadow_lock:
        _last_shadow_result.clear()
        _last_shadow_result.update(result)

    return result


# ── Logging ────────────────────────────────────────────────────────────────────

def log_shadow_memory_result(result: dict) -> None:
    """Append a shadow comparison result to the JSONL log.

    Writes only safe metadata — no user secrets, no raw payloads.
    """
    assert _SUPABASE_WRITE_ATTEMPTED is False
    try:
        SHADOW_LOG_DIR.mkdir(parents=True, exist_ok=True)
        safe_result = {k: v for k, v in result.items() if k not in ("raw_message",)}
        with SHADOW_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe_result, default=str) + "\n")
    except Exception as exc:
        logger.warning("shadow log write failed: %s", exc)


# ── Background trigger ─────────────────────────────────────────────────────────

def trigger_shadow_comparison_async(
    user_message: str,
    current_context: dict | None = None,
    current_response: str | None = None,
) -> None:
    """Fire-and-forget shadow comparison in a daemon thread.

    Does NOT block the caller. Failures are logged and silently swallowed.
    """
    def _run():
        try:
            run_shadow_memory_comparison(user_message, current_context, current_response)
        except Exception as exc:
            logger.debug("shadow async comparison error (non-fatal): %s", exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


# ── Status formatter ───────────────────────────────────────────────────────────

def format_shadow_status() -> str:
    """Format a human-readable status block for 'show memory v2 shadow status'."""
    mode = get_memory_v2_mode()
    primary_blocked = is_primary_mode_requested()

    lines = ["HERMES MEMORY V2 SHADOW STATUS", ""]

    if primary_blocked:
        lines += [
            "WARNING: Primary mode requested but BLOCKED.",
            "Primary requested but blocked. Ray approval phase required.",
            "",
        ]

    lines += [
        f"Mode: {mode}",
        "",
        "Live Telegram reader: current active reader",
        "Memory v2: loaded in shadow only" if mode == MODE_SHADOW else f"Memory v2: {mode} mode",
        "",
    ]

    # Try to get live v2 counts
    try:
        from lib.hermes_memory_v2_reader import _total_count, _count_by_type, _env_available
        if _env_available():
            total = _total_count()
            lines.append(f"Rows: {total} active/live_answer")
            for mt in PLANNED_BATCH_TYPES:
                cnt = _count_by_type(mt)
                if cnt > 0:
                    lines.append(f"  {mt}: {cnt}")
        else:
            lines.append("Rows: unavailable (credentials not in local env)")
    except Exception:
        lines.append("Rows: unavailable")

    lines.append("")

    # Last shadow comparison
    with _shadow_lock:
        last = dict(_last_shadow_result)

    if last:
        lines += [
            "Last shadow comparison:",
            f"  timestamp: {last.get('timestamp', 'unknown')}",
            f"  coverage: {last.get('overlap_summary', 'unknown')}",
            f"  risk flags: {last.get('risk_flags') or 'none'}",
            f"  recommendation: {last.get('recommendation', '')}",
        ]
    else:
        lines.append("Last shadow comparison: none yet")

    lines += [
        "",
        "Important: Shadow mode does not change Hermes answers.",
        "Primary mode requires Ray approval.",
    ]

    return "\n".join(lines)


def format_v2_live_status() -> str:
    """Short status for 'is memory v2 live / primary / shadow only' queries."""
    mode = get_memory_v2_mode()
    primary_blocked = is_primary_mode_requested()

    if primary_blocked:
        return (
            "Primary mode is not enabled and requires Ray approval.\n"
            "Current mode: shadow (primary blocked).\n"
            "Live answers still use current active reader."
        )
    if mode == MODE_SHADOW:
        return (
            "Memory v2 is shadow only. "
            "Live answers still use current reader."
        )
    if mode == MODE_OFF:
        return "Memory v2 is off. Live answers use current reader only."
    return (
        "Memory v2 is preview only. "
        "Live answers use current reader."
    )
