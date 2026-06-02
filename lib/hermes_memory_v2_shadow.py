"""
hermes_memory_v2_shadow.py
Phase 4E/4F: Shadow + primary reader mode for hermes_memory_v2.

Mode config via HERMES_MEMORY_V2_MODE env var:
  off      — do not load v2 at all
  preview  — only explicit preview commands read v2 (default)
  shadow   — v2 loads in background for comparison/logging only
  primary  — structured memory primary; requires approval file + all guards

Primary mode requires ALL of:
  1. HERMES_MEMORY_V2_MODE=primary
  2. docs/reports/memory/hermes_memory_v2_primary_approval.json exists
  3. approval phrase matches exactly
  4. hermes_memory_v2 has all 8 planned safe types
  5. active/live_answer row count >= 26
  6. no risk flags from v2 reader
  7. stale/blocked strings check passes
  8. shadow log exists and last entries have live_response_changed=False

If any condition fails: fall back to shadow, log warning, do not crash.

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
MODE_PRIMARY = "primary"

# primary is now in _VALID_MODES but requires approval guards to activate
_VALID_MODES = {MODE_OFF, MODE_PREVIEW, MODE_SHADOW, MODE_PRIMARY}

# ── Approval config ────────────────────────────────────────────────────────────
REQUIRED_APPROVAL_PHRASE = "I APPROVE HERMES MEMORY V2 PRIMARY MODE SWITCH"
PRIMARY_MIN_ROWS          = 26
PRIMARY_REQUIRED_TYPES    = (
    "operating_rule", "ray_preference", "approval_policy", "project_context",
    "lesson", "goal", "tool_registry", "scout_registry",
)

_ROOT            = Path(__file__).resolve().parent.parent
APPROVAL_FILE    = _ROOT / "docs" / "reports" / "memory" / "hermes_memory_v2_primary_approval.json"

# ── Planned Batch 1/2 type coverage ───────────────────────────────────────────
PLANNED_BATCH_TYPES: tuple[str, ...] = PRIMARY_REQUIRED_TYPES

# ── Types always excluded from current-truth reads ────────────────────────────
EXCLUDED_FROM_CURRENT_TRUTH: tuple[str, ...] = (
    "provider_status_snapshot", "executive_briefings",
    "ai_task_queue", "agent_dispatch_tasks",
    "fallback_rule", "debug_note", "archived_note",
    "template",
)

# ── Shadow log path ────────────────────────────────────────────────────────────
SHADOW_LOG_DIR  = _ROOT / "docs" / "reports" / "memory" / "shadow"
SHADOW_LOG_PATH = SHADOW_LOG_DIR / "hermes_memory_v2_shadow_log.jsonl"

# ── In-memory cache of last shadow result (for status command) ─────────────────
_last_shadow_result: dict = {}
_shadow_lock = threading.Lock()

# ── In-memory primary mode state (set after guard check) ──────────────────────
_primary_active: bool = False
_primary_active_lock = threading.Lock()
_primary_guard_failures: list[str] = []


# ── Primary mode approval guard ────────────────────────────────────────────────

def _check_primary_approval_guards() -> tuple[bool, list[str]]:
    """Run all guards for primary mode activation.

    Returns (ok, failures). If ok=False, failures lists what blocked it.
    Does not raise.
    """
    failures: list[str] = []

    # Guard 1: approval file exists
    if not APPROVAL_FILE.exists():
        failures.append(f"approval file missing: {APPROVAL_FILE.name}")

    # Guard 2: approval phrase matches
    else:
        try:
            doc = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
            phrase = doc.get("approval_phrase", "")
            if phrase != REQUIRED_APPROVAL_PHRASE:
                failures.append(
                    f"approval_phrase mismatch in {APPROVAL_FILE.name}"
                )
            if doc.get("mode") != "primary":
                failures.append("approval file mode != 'primary'")
        except Exception as exc:
            failures.append(f"approval file unreadable: {exc}")

    # Guards 3-6: live Supabase check
    try:
        from lib.hermes_memory_v2_reader import (
            build_v2_memory_context_pack,
            _env_available,
            _STALE_MARKERS,
        )
        if not _env_available():
            failures.append("Supabase credentials not available")
        else:
            pack = build_v2_memory_context_pack(limit=50)
            total = pack.get("total", 0)
            by_type = pack.get("by_type", {})

            # Guard 3: row count
            if total < PRIMARY_MIN_ROWS:
                failures.append(
                    f"row count {total} < required {PRIMARY_MIN_ROWS}"
                )

            # Guard 4: all 8 types present
            missing = [t for t in PRIMARY_REQUIRED_TYPES if by_type.get(t, 0) == 0]
            if missing:
                failures.append(f"planned types missing: {missing}")

            # Guard 5: no risk flags (missing_from_v2 = [])
            from lib.hermes_memory_v2_reader import compare_v2_with_current_memory
            cmp = compare_v2_with_current_memory()
            if cmp.get("missing_from_v2"):
                failures.append(
                    f"missing_from_v2 non-empty: {cmp['missing_from_v2']}"
                )

            # Guard 6: stale check on titles
            records = pack.get("records", [])
            from lib.hermes_memory_v2_reader import _has_stale
            for r in records[:20]:
                title = r.get("title", "")
                if _has_stale(title):
                    failures.append(f"stale marker in record title: {title[:50]}")
                    break

    except Exception as exc:
        failures.append(f"v2 reader guard error: {exc}")

    # Guard 7: shadow log sanity check
    if SHADOW_LOG_PATH.exists():
        try:
            lines = [
                json.loads(l)
                for l in SHADOW_LOG_PATH.read_text().strip().splitlines()[-10:]
                if l.strip()
            ]
            bad = [l for l in lines if l.get("live_response_changed") is not False]
            if bad:
                failures.append(
                    f"shadow log has {len(bad)} entries with live_response_changed != False"
                )
        except Exception as exc:
            failures.append(f"shadow log unreadable: {exc}")
    else:
        failures.append("shadow log does not exist — run shadow mode first")

    return (len(failures) == 0), failures


def is_primary_approved() -> tuple[bool, list[str]]:
    """Return (approved, failures) for primary mode activation."""
    return _check_primary_approval_guards()


# ── Mode helpers ───────────────────────────────────────────────────────────────

def get_memory_v2_mode() -> str:
    """Return the effective HERMES_MEMORY_V2_MODE.

    For 'primary': runs all approval guards. Falls back to shadow if any fail.
    For invalid values: falls back to preview.
    """
    global _primary_active, _primary_guard_failures
    raw = os.environ.get("HERMES_MEMORY_V2_MODE", MODE_PREVIEW).strip().lower()

    if raw not in _VALID_MODES:
        logger.warning(
            "HERMES_MEMORY_V2_MODE=%r is invalid — falling back to preview.", raw
        )
        return MODE_PREVIEW

    if raw == MODE_PRIMARY:
        ok, failures = _check_primary_approval_guards()
        with _primary_active_lock:
            _primary_active = ok
            _primary_guard_failures = failures
        if not ok:
            logger.warning(
                "HERMES_MEMORY_V2_MODE=primary blocked — guard failures: %s — "
                "falling back to shadow.", failures
            )
            return MODE_SHADOW
        logger.info("HERMES_MEMORY_V2_MODE=primary: all guards passed, primary active.")
        return MODE_PRIMARY

    with _primary_active_lock:
        _primary_active = False
        _primary_guard_failures = []
    return raw


def is_primary_mode_active() -> bool:
    """Return True only if primary mode is fully guarded and active."""
    return get_memory_v2_mode() == MODE_PRIMARY


def is_primary_mode_requested() -> bool:
    """Return True if env var is set to 'primary' (regardless of guard status)."""
    return os.environ.get("HERMES_MEMORY_V2_MODE", "").strip().lower() == MODE_PRIMARY


def is_shadow_mode_enabled() -> bool:
    """Return True if the effective mode is shadow."""
    return get_memory_v2_mode() == MODE_SHADOW


def get_primary_guard_failures() -> list[str]:
    """Return the list of guard failures from the last primary mode attempt."""
    with _primary_active_lock:
        return list(_primary_guard_failures)


# ── Primary memory context loader ──────────────────────────────────────────────

def load_primary_memory_context() -> dict:
    """Load hermes_memory_v2 as primary structured memory source.

    Priority contract (primary mode only):
      1. Current conversation context / fresh artifacts override everything
      2. hermes_memory_v2 active/live_answer records (structured memory)
      3. Live provider policy stays separate
      4. Archived/debug/stale records are excluded

    Returns a safe context dict — no payloads, no secrets.
    """
    assert _SUPABASE_WRITE_ATTEMPTED is False
    try:
        from lib.hermes_memory_v2_reader import build_v2_memory_context_pack
        pack = build_v2_memory_context_pack(limit=50)
        return {
            "source":       "hermes_memory_v2_primary",
            "available":    pack.get("available", False),
            "total":        pack.get("total", 0),
            "by_type":      pack.get("by_type", {}),
            "records":      pack.get("records", []),
            "excluded":     list(EXCLUDED_FROM_CURRENT_TRUTH),
            "priority_note": (
                "Current conversation context and fresh artifacts "
                "override this structured memory."
            ),
        }
    except Exception as exc:
        logger.warning("load_primary_memory_context error: %s", exc)
        return {
            "source": "hermes_memory_v2_primary",
            "available": False,
            "error": str(exc),
        }


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
    """Compare current reader context with v2 context. Returns safe metadata only."""
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

    present = [t for t in PLANNED_BATCH_TYPES if v2_by_type.get(t, 0) > 0]
    missing = [t for t in PLANNED_BATCH_TYPES if v2_by_type.get(t, 0) == 0]

    risk_flags: list[str] = []
    if not v2_available:
        risk_flags.append("v2_unavailable")
    if missing:
        risk_flags.append(f"planned_types_missing: {missing}")

    coverage_pct = round(len(present) / len(PLANNED_BATCH_TYPES) * 100) if PLANNED_BATCH_TYPES else 0

    if missing:
        recommendation = (
            f"v2 is missing planned types: {missing}. Keep in preview/shadow."
        )
    else:
        recommendation = (
            "Batch 1/2 coverage complete. v2 shadow mode active. "
            "Primary mode requires Ray approval."
        )

    return {
        "v2_available":          v2_available,
        "v2_total":              v2_total,
        "v2_by_type":            v2_by_type,
        "current_sources":       current_sources,
        "planned_types_count":   len(PLANNED_BATCH_TYPES),
        "present_count":         len(present),
        "missing_types":         missing,
        "coverage_pct":          coverage_pct,
        "risk_flags":            risk_flags,
        "recommendation":        recommendation,
        "live_response_changed": False,
    }


# ── Shadow run ─────────────────────────────────────────────────────────────────

def run_shadow_memory_comparison(
    user_message: str,
    current_context: dict | None = None,
    current_response: str | None = None,
) -> dict:
    """Run a shadow comparison and log result. Never modifies current_response."""
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
    """Append a shadow comparison result to the JSONL log. Safe metadata only."""
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
    """Fire-and-forget shadow comparison in a daemon thread. Never blocks caller."""
    def _run():
        try:
            run_shadow_memory_comparison(user_message, current_context, current_response)
        except Exception as exc:
            logger.debug("shadow async comparison error (non-fatal): %s", exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


# ── Status formatters ──────────────────────────────────────────────────────────

def format_primary_status() -> str:
    """Format status block for 'show memory v2 primary status'."""
    mode = get_memory_v2_mode()
    failures = get_primary_guard_failures()

    lines = ["HERMES MEMORY V2 PRIMARY STATUS", ""]

    if mode == MODE_PRIMARY:
        lines += ["Mode: primary", "", "Status: active for structured memory", ""]
    else:
        lines += [
            f"Mode: {mode} (primary not active)",
            "",
        ]
        if failures:
            lines.append("Guard failures:")
            for f in failures:
                lines.append(f"  - {f}")
            lines.append("")

    # Row counts from live Supabase
    try:
        from lib.hermes_memory_v2_reader import _total_count, _count_by_type, _env_available
        if _env_available():
            total = _total_count()
            lines.append(f"Rows: {total} active/live_answer")
            lines.append("")
            lines.append("Loaded types:")
            for mt in PLANNED_BATCH_TYPES:
                cnt = _count_by_type(mt)
                if cnt > 0:
                    lines.append(f"  {mt}: {cnt}")
        else:
            lines.append("Rows: unavailable (credentials not in this env)")
    except Exception:
        lines.append("Rows: unavailable")

    lines += [
        "",
        "Safety:",
        "  archived/deprecated/blocked/debug records excluded",
        "  stale strings excluded",
        "  provider snapshots not used as current truth",
        "  live provider policy remains separate",
        "  artifacts/actions/decisions/source intake still have priority",
        "",
        "Rollback:",
        "  Set HERMES_MEMORY_V2_MODE=shadow and restart Telegram bot.",
        "  Or run: python scripts/rollback_hermes_memory_v2_primary.py --apply",
    ]
    return "\n".join(lines)


def format_shadow_status() -> str:
    """Format status block for 'show memory v2 shadow status'."""
    mode = get_memory_v2_mode()
    primary_blocked = is_primary_mode_requested() and mode != MODE_PRIMARY

    lines = ["HERMES MEMORY V2 SHADOW STATUS", ""]

    if primary_blocked:
        failures = get_primary_guard_failures()
        lines += [
            "WARNING: Primary mode requested but guards failed.",
            "Primary requested but blocked. Ray approval phase required.",
        ]
        if failures:
            for f in failures:
                lines.append(f"  - {f}")
        lines.append("")

    lines += [
        f"Mode: {mode}",
        "",
        "Live Telegram reader: current active reader",
    ]
    if mode == MODE_PRIMARY:
        lines.append("Memory v2: PRIMARY for structured memory")
    elif mode == MODE_SHADOW:
        lines.append("Memory v2: loaded in shadow only")
    else:
        lines.append(f"Memory v2: {mode} mode")
    lines.append("")

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

    if mode == MODE_PRIMARY:
        return (
            "Memory v2 is PRIMARY for structured memory. "
            "Current artifacts/actions/decisions still override stale memory."
        )
    if is_primary_mode_requested() and mode != MODE_PRIMARY:
        failures = get_primary_guard_failures()
        failure_summary = "; ".join(failures[:2]) if failures else "unknown"
        return (
            f"Primary mode requested but blocked ({failure_summary}). "
            "Current mode: shadow. Live answers still use current reader."
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
