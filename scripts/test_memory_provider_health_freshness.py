"""
test_memory_provider_health_freshness.py
Verifies Phase 3B provider_health freshness classification rules.
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_memory_freshness import (
    classify_provider_health_record,
    is_provider_health_fresh,
    PROVIDER_HEALTH_MAX_AGE_MIN,
    _PROVIDER_STALE_VALUES,
)

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def ts_ago(minutes: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return dt.isoformat()


print("=== test_memory_provider_health_freshness ===\n")

# ── Constants ─────────────────────────────────────────────────────────────────
print("-- Constants --")
check("PROVIDER_HEALTH_MAX_AGE_MIN == 15", PROVIDER_HEALTH_MAX_AGE_MIN == 15)
check("'OFFLINE' in stale values", "OFFLINE" in _PROVIDER_STALE_VALUES)
check("'Ollama OFFLINE' in stale values", "Ollama OFFLINE" in _PROVIDER_STALE_VALUES)
check("'Beehiiv pending' in stale values", "Beehiiv pending" in _PROVIDER_STALE_VALUES)
check("'YouTube Studio pending' in stale values", "YouTube Studio pending" in _PROVIDER_STALE_VALUES)
check("'OpenRouter not configured' in stale values", "OpenRouter not configured" in _PROVIDER_STALE_VALUES)

# ── Fresh healthy record ──────────────────────────────────────────────────────
print("\n-- Fresh healthy record (10 min old, status=ok) --")
fresh_ok = {"updated_at": ts_ago(10), "status": "ok"}
check("classify → active_live_answer", classify_provider_health_record(fresh_ok) == "active_live_answer")
check("is_fresh → True", is_provider_health_fresh(fresh_ok))

# ── Fresh OFFLINE record ──────────────────────────────────────────────────────
print("\n-- Fresh OFFLINE record (5 min old) --")
fresh_offline = {"updated_at": ts_ago(5), "status": "OFFLINE"}
check("classify → needs_review (not blocked — fresh)", classify_provider_health_record(fresh_offline) == "needs_review")
check("is_fresh → False (OFFLINE not active answer)", not is_provider_health_fresh(fresh_offline))

# ── Stale healthy record ──────────────────────────────────────────────────────
print("\n-- Stale healthy record (20 min old, status=ok) --")
stale_ok = {"updated_at": ts_ago(20), "status": "ok"}
check("classify → historical_only", classify_provider_health_record(stale_ok) == "historical_only")
check("is_fresh → False", not is_provider_health_fresh(stale_ok))

# ── Stale OFFLINE record ──────────────────────────────────────────────────────
print("\n-- Stale OFFLINE record (30 min old) --")
stale_offline = {"updated_at": ts_ago(30), "status": "OFFLINE"}
check("classify → blocked_from_live", classify_provider_health_record(stale_offline) == "blocked_from_live")
check("is_fresh → False", not is_provider_health_fresh(stale_offline))

# ── Stale Ollama OFFLINE ──────────────────────────────────────────────────────
print("\n-- Stale Ollama OFFLINE (2h old) --")
stale_ollama = {"updated_at": ts_ago(120), "health": "Ollama OFFLINE"}
check("classify → blocked_from_live", classify_provider_health_record(stale_ollama) == "blocked_from_live")

# ── No timestamp ──────────────────────────────────────────────────────────────
print("\n-- No timestamp --")
no_ts = {"status": "ok"}
check("classify → needs_review", classify_provider_health_record(no_ts) == "needs_review")
check("is_fresh → False", not is_provider_health_fresh(no_ts))

# ── Boundary: near 15 minutes ─────────────────────────────────────────────────
print("\n-- Boundary near 15 minutes --")
at_boundary = {"updated_at": ts_ago(14.9), "status": "ok"}
# Just under 15min should be active
check("at 14.9min → active_live_answer", classify_provider_health_record(at_boundary) == "active_live_answer")

at_boundary_plus = {"updated_at": ts_ago(15.1), "status": "ok"}
check("at 15.1min → historical_only", classify_provider_health_record(at_boundary_plus) == "historical_only")

# ── alternate timestamp fields ────────────────────────────────────────────────
print("\n-- Alternate timestamp fields --")
checked_at_rec = {"checked_at": ts_ago(5), "status": "ok"}
check("checked_at field recognized", classify_provider_health_record(checked_at_rec) == "active_live_answer")
timestamp_rec = {"timestamp": ts_ago(5), "status": "ok"}
check("timestamp field recognized", classify_provider_health_record(timestamp_rec) == "active_live_answer")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
