"""
test_backfill_hermes_memory_v2_blocks_stale_strings.py
Verifies stale marker detection in _validate_record and _has_stale_marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "backfill_hermes_memory_v2.py"
sys.path.insert(0, str(ROOT / "scripts"))

PASS = 0; FAIL = 0

STALE_STRINGS = [
    "Ollama OFFLINE",
    "Beehiiv pending",
    "YouTube Studio pending",
    "OpenRouter not configured",
    "Quality escalation fallback",
    "Executive Memory — as of",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_backfill_hermes_memory_v2_blocks_stale_strings ===\n")

check("backfill_hermes_memory_v2.py exists", SCRIPT.exists())
if not SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = SCRIPT.read_text(encoding="utf-8")

print("-- STALE_MARKERS defined in source --")
check("STALE_MARKERS list defined", "STALE_MARKERS" in src)
for s in STALE_STRINGS:
    check(f"stale marker present: {s!r}", s in src)

print("\n-- _has_stale_marker() function --")
check("_has_stale_marker function defined", "_has_stale_marker" in src)
check("checks title field", "title" in src and "_has_stale_marker" in src)
check("checks summary field", "summary" in src and "_has_stale_marker" in src)
check("case-insensitive check", ".lower()" in src)

print("\n-- _validate_record rejects stale records --")
check("_validate_record calls _has_stale_marker", "_has_stale_marker" in src and "_validate_record" in src)
check("stale detection adds to errors list", "stale marker detected" in src)

print("\n-- Runtime stale marker tests --")
from backfill_hermes_memory_v2 import _has_stale_marker, _validate_record, BATCH_ALLOWED_TYPES

batch1_types = BATCH_ALLOWED_TYPES.get("batch1", set())

def make_record(**kwargs):
    base = {
        "memory_id": "test-stale",
        "title": "Normal title",
        "summary": "Normal summary",
        "memory_type": "operating_rule",
        "status": "active",
        "scope": "live_answer",
        "confidence": 0.9,
        "priority": 1,
        "tags": [],
        "payload": {},
        "migration_status": "dry_run",
        "created_at": "2026-06-02T00:00:00Z",
        "updated_at": "2026-06-02T00:00:00Z",
    }
    base.update(kwargs)
    return base

for stale_str in STALE_STRINGS:
    r_title = make_record(title=f"Some info: {stale_str} config note")
    result_t = _has_stale_marker(r_title)
    check(f"_has_stale_marker detects in title: {stale_str[:30]!r}", result_t is not None)

    r_summary = make_record(summary=f"Details: {stale_str.lower()} — see logs")
    result_s = _has_stale_marker(r_summary)
    check(f"_has_stale_marker detects case-insensitive in summary: {stale_str[:30]!r}", result_s is not None)

    r_stale = make_record(title=stale_str)
    errs = _validate_record(r_stale, batch1_types)
    check(f"_validate_record rejects stale record: {stale_str[:30]!r}", len(errs) > 0)
    check(f"error mentions stale: {stale_str[:30]!r}",
          any("stale" in e.lower() for e in errs))

# Clean record should pass
clean = make_record()
clean_errs = _validate_record(clean, batch1_types)
check("clean record passes stale marker check", not any("stale" in e.lower() for e in clean_errs))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
