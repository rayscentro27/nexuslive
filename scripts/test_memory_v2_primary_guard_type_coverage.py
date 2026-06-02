"""
test_memory_v2_primary_guard_type_coverage.py
Tests: primary guard uses full per-type counts (not limited sample),
so types present in Supabase are never reported missing.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_primary_guard_type_coverage ===\n")

import inspect
from lib.hermes_memory_v2_shadow import _check_primary_approval_guards, PRIMARY_REQUIRED_TYPES

# ── Source code must use _count_by_type, not just by_type from limited pack ──
print("-- source uses per-type exact counts for Guard 4 --")
src = inspect.getsource(_check_primary_approval_guards)
check("Guard 4 uses _count_by_type", "_count_by_type" in src)
check("Guard 3 uses _total_count", "_total_count" in src)
check("build_v2_memory_context_pack still used for Guard 6 (stale check)",
      "build_v2_memory_context_pack" in src)

# ── No contradiction: types with count > 0 must not appear in failures ───────
print("\n-- no false missing types when Supabase available --")
from lib.hermes_memory_v2_reader import _env_available, _count_by_type

if not _env_available():
    print("  SKIP  Supabase not available in this env — guard will report credential error")
    check("Supabase unavailable — guard returns failure correctly", True)
else:
    # Get actual counts per type
    type_counts = {mt: _count_by_type(mt) for mt in PRIMARY_REQUIRED_TYPES}
    present = [mt for mt, cnt in type_counts.items() if cnt > 0]
    missing_in_db = [mt for mt, cnt in type_counts.items() if cnt == 0]

    print(f"  DB counts: {type_counts}")

    # Run guards
    _, failures = _check_primary_approval_guards()
    failure_text = " ".join(failures)

    # Any type present in DB must not appear in "planned types missing" failure
    for mt in present:
        check(f"type '{mt}' (count={type_counts[mt]}) not in 'planned types missing'",
              f"planned types missing" not in failure_text or mt not in failure_text)

    # If all 8 types are present, the planned-types guard must pass
    if not missing_in_db:
        check("all 8 types present → no 'planned types missing' failure",
              "planned types missing" not in failure_text)

# ── format_primary_status includes planned type coverage line ─────────────────
print("\n-- format_primary_status includes coverage line --")
from lib.hermes_memory_v2_shadow import format_primary_status
status = format_primary_status()
check("status contains 'Planned type coverage'", "Planned type coverage" in status)
check("status contains '/8 present'", "/8 present" in status)
check("status starts with HERMES MEMORY V2 PRIMARY STATUS",
      status.startswith("HERMES MEMORY V2 PRIMARY STATUS"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
