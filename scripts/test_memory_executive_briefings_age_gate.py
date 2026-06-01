"""
test_memory_executive_briefings_age_gate.py
Verifies Phase 3B executive_briefings 48-hour age gate rules.
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_memory_freshness import (
    classify_executive_briefing,
    is_briefing_fresh,
    briefing_age_hours,
    BRIEFING_MAX_AGE_H,
)

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def ts_ago_hours(h: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=h)
    return dt.isoformat()


print("=== test_memory_executive_briefings_age_gate ===\n")

# ── Constants ─────────────────────────────────────────────────────────────────
print("-- Constants --")
check("BRIEFING_MAX_AGE_H == 48", BRIEFING_MAX_AGE_H == 48)

# ── Fresh briefing (< 48h) ────────────────────────────────────────────────────
print("\n-- Fresh briefing (1h old) --")
fresh = {"created_at": ts_ago_hours(1)}
check("classify → active_live_answer", classify_executive_briefing(fresh) == "active_live_answer")
check("is_fresh → True", is_briefing_fresh(fresh))
age = briefing_age_hours(fresh)
check("age is between 0.9 and 1.1 hours", age is not None and 0.9 < age < 1.1)

print("\n-- Fresh briefing (47h old) --")
almost_stale = {"created_at": ts_ago_hours(47)}
check("classify → active_live_answer", classify_executive_briefing(almost_stale) == "active_live_answer")
check("is_fresh → True", is_briefing_fresh(almost_stale))

# ── Stale briefing (> 48h) ────────────────────────────────────────────────────
print("\n-- Stale briefing (49h old) --")
stale = {"created_at": ts_ago_hours(49)}
check("classify → historical_only", classify_executive_briefing(stale) == "historical_only")
check("is_fresh → False", not is_briefing_fresh(stale))

print("\n-- Very stale briefing (7 days old) --")
very_stale = {"updated_at": ts_ago_hours(168)}
check("classify → historical_only", classify_executive_briefing(very_stale) == "historical_only")
check("is_fresh → False", not is_briefing_fresh(very_stale))

# ── Boundary near 48h ─────────────────────────────────────────────────────────
print("\n-- Boundary near 48h --")
at_48 = {"created_at": ts_ago_hours(47.9)}
# Just under 48h should be active
check("at 47.9h → active_live_answer", classify_executive_briefing(at_48) == "active_live_answer")

at_48_plus = {"created_at": ts_ago_hours(48.1)}
check("at 48.1h → historical_only", classify_executive_briefing(at_48_plus) == "historical_only")

# ── No timestamp ──────────────────────────────────────────────────────────────
print("\n-- No timestamp --")
no_ts = {"content": "briefing text"}
check("classify → needs_review", classify_executive_briefing(no_ts) == "needs_review")
check("is_fresh → False", not is_briefing_fresh(no_ts))
check("briefing_age_hours → None", briefing_age_hours(no_ts) is None)

# ── Alternate timestamp fields ────────────────────────────────────────────────
print("\n-- Alternate timestamp fields --")
check("updated_at field works", is_briefing_fresh({"updated_at": ts_ago_hours(1)}))
check("generated_at field works", is_briefing_fresh({"generated_at": ts_ago_hours(1)}))
check("timestamp field works", is_briefing_fresh({"timestamp": ts_ago_hours(1)}))

# ── Age gate prevents stale briefings from live answers ───────────────────────
print("\n-- Stale briefings must not be live answers --")
briefings_checked = []
for age_h in [0.5, 1, 6, 12, 24, 47]:
    b = {"created_at": ts_ago_hours(age_h)}
    briefings_checked.append(is_briefing_fresh(b))
check("all briefings <48h are fresh", all(briefings_checked))

stale_briefings = []
for age_h in [48.1, 72, 96, 168]:
    b = {"created_at": ts_ago_hours(age_h)}
    stale_briefings.append(not is_briefing_fresh(b))
check("all briefings >48h are not fresh", all(stale_briefings))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
