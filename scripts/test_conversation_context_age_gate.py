"""
test_conversation_context_age_gate.py
Verifies Phase 3B conversation context 24-hour age gate and follow-up resolution safety.
"""
import sys
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_memory_freshness import (
    classify_conversation_context,
    is_context_fresh,
    stale_context_clarification,
    CONTEXT_MAX_AGE_H,
)

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def ts_ago_hours(h: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=h)
    return dt.isoformat()


print("=== test_conversation_context_age_gate ===\n")

# ── Constants ─────────────────────────────────────────────────────────────────
print("-- Constants --")
check("CONTEXT_MAX_AGE_H == 24", CONTEXT_MAX_AGE_H == 24)

# ── Fresh context ─────────────────────────────────────────────────────────────
print("\n-- Fresh context (1h old) --")
fresh = {"timestamp": ts_ago_hours(1), "primary_object_type": "content_draft"}
check("classify → active_live_answer", classify_conversation_context(fresh) == "active_live_answer")
check("is_fresh → True", is_context_fresh(fresh))

print("\n-- Fresh context (23h old) --")
almost_stale = {"timestamp": ts_ago_hours(23)}
check("classify → active_live_answer", classify_conversation_context(almost_stale) == "active_live_answer")
check("is_fresh → True", is_context_fresh(almost_stale))

# ── Stale context ─────────────────────────────────────────────────────────────
print("\n-- Stale context (25h old) --")
stale = {"timestamp": ts_ago_hours(25)}
check("classify → historical_only", classify_conversation_context(stale) == "historical_only")
check("is_fresh → False", not is_context_fresh(stale))

print("\n-- Very stale context (3 days old) --")
very_stale = {"timestamp": ts_ago_hours(72)}
check("classify → historical_only", classify_conversation_context(very_stale) == "historical_only")
check("is_fresh → False", not is_context_fresh(very_stale))

# ── Boundary near 24h ────────────────────────────────────────────────────────
print("\n-- Boundary near 24h --")
at_24 = {"timestamp": ts_ago_hours(23.9)}
check("at 23.9h → active_live_answer", classify_conversation_context(at_24) == "active_live_answer")

at_24_plus = {"timestamp": ts_ago_hours(24.1)}
check("at 24.1h → historical_only", classify_conversation_context(at_24_plus) == "historical_only")

# ── No timestamp ──────────────────────────────────────────────────────────────
print("\n-- No timestamp --")
no_ts = {"primary_object_type": "action"}
check("classify → needs_review", classify_conversation_context(no_ts) == "needs_review")
check("is_fresh → False", not is_context_fresh(no_ts))

# ── Stale clarification message ───────────────────────────────────────────────
print("\n-- Stale clarification message --")
msg = stale_context_clarification()
check("clarification is a non-empty string", isinstance(msg, str) and len(msg) > 20)
check("clarification mentions 24 hours", "24" in msg)
check("clarification offers to help with draft or actions", "draft" in msg.lower() or "action" in msg.lower())

# ── get_last_context age gate ─────────────────────────────────────────────────
print("\n-- get_last_context() age gate integration --")
import lib.hermes_conversation_context_resolver as resolver

with tempfile.TemporaryDirectory() as tmpdir:
    ctx_file = Path(tmpdir) / "hermes_conversation_context.json"

    # Fresh context should be returned
    fresh_ctx = {"timestamp": ts_ago_hours(1), "primary_object_type": "content_draft",
                 "primary_object_title": "test draft"}
    ctx_file.write_text(json.dumps(fresh_ctx))
    with patch.object(resolver, "_CONTEXT_FILE", ctx_file):
        result = resolver.get_last_context()
    check("get_last_context returns fresh context", result is not None)
    check("fresh context has correct title", result is not None and result.get("primary_object_title") == "test draft")

    # Stale context should be blocked
    stale_ctx = {"timestamp": ts_ago_hours(30), "primary_object_type": "action",
                 "primary_object_title": "old action"}
    ctx_file.write_text(json.dumps(stale_ctx))
    with patch.object(resolver, "_CONTEXT_FILE", ctx_file):
        result_stale = resolver.get_last_context()
    check("get_last_context returns None for stale context", result_stale is None)

    # get_last_context_any_age should still return stale
    with patch.object(resolver, "_CONTEXT_FILE", ctx_file):
        result_any = resolver.get_last_context_any_age()
    check("get_last_context_any_age returns stale context", result_any is not None)
    check("any_age context has stale title", result_any is not None and result_any.get("primary_object_title") == "old action")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
