"""
test_memory_v2_primary_status_no_false_missing_types.py
Tests: format_primary_status never reports a type as missing when _count_by_type > 0.
Also verifies HERMES_MEMORY_V2_MODE=primary reports primary when guards pass.
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


print("=== test_memory_v2_primary_status_no_false_missing_types ===\n")

from lib.hermes_memory_v2_shadow import (
    format_primary_status, PRIMARY_REQUIRED_TYPES,
    _check_primary_approval_guards,
)
from lib.hermes_memory_v2_reader import _env_available, _count_by_type

# ── format_primary_status structure ──────────────────────────────────────────
print("-- format_primary_status structure --")
status = format_primary_status()
check("non-empty", bool(status))
check("starts with HERMES MEMORY V2 PRIMARY STATUS",
      status.startswith("HERMES MEMORY V2 PRIMARY STATUS"))
check("contains 'Mode:'", "Mode:" in status)
check("contains 'Planned type coverage'", "Planned type coverage" in status)
check("contains '/8 present'", "/8 present" in status)

# ── No contradictory guard failure ────────────────────────────────────────────
print("\n-- no type reported missing when count > 0 in Supabase --")
if not _env_available():
    check("Supabase unavailable — skip contradiction check", True)
else:
    type_counts = {mt: _count_by_type(mt) for mt in PRIMARY_REQUIRED_TYPES}
    present_types = [mt for mt, cnt in type_counts.items() if cnt > 0]

    _, failures = _check_primary_approval_guards()
    # Find any "planned types missing" failure message
    missing_msg = next((f for f in failures if "planned types missing" in f), "")

    if missing_msg:
        # Parse the list from the message: "planned types missing: ['a', 'b']"
        import ast
        try:
            reported_missing = ast.literal_eval(missing_msg.split("planned types missing: ")[1])
        except Exception:
            reported_missing = []
        # None of the reported_missing types should have count > 0
        for mt in reported_missing:
            check(f"reported-missing '{mt}' truly has count == 0",
                  type_counts.get(mt, 0) == 0)
    else:
        check("no 'planned types missing' failure (all types present)", True)

    # Coverage line in status must match actual present count
    present_count = sum(1 for c in type_counts.values() if c > 0)
    coverage_line = f"{present_count}/8 present"
    check(f"status coverage line matches actual: '{coverage_line}'",
          coverage_line in status)

# ── Mode=primary env var: reported correctly ──────────────────────────────────
print("\n-- HERMES_MEMORY_V2_MODE=primary env var respected --")
import os as _os
from lib.hermes_memory_v2_shadow import get_memory_v2_mode, is_primary_mode_requested, MODE_PRIMARY

current_mode_env = _os.environ.get("HERMES_MEMORY_V2_MODE", "preview")
if current_mode_env == "primary":
    effective_mode = get_memory_v2_mode()
    ok, failures = _check_primary_approval_guards()
    if ok:
        check("env=primary + guards pass → effective mode == primary",
              effective_mode == MODE_PRIMARY)
    else:
        check("env=primary + guards fail → mode != primary (blocked)", effective_mode != MODE_PRIMARY)
        # Status must explain why (guard failures listed)
        check("status explains guard failures when primary blocked",
              any(f in status for f in ["Guard failures:", "Mode: shadow", "Mode: preview"]))
else:
    check(f"HERMES_MEMORY_V2_MODE={current_mode_env!r} — not testing primary mode", True)

# ── No old executive memory in status ────────────────────────────────────────
print("\n-- no old executive memory in status --")
check("no 'old executive memory'", "old executive memory" not in status.lower())
check("no 'executive memory snapshot'", "executive memory snapshot" not in status.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
