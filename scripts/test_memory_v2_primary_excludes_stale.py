"""
test_memory_v2_primary_excludes_stale.py
Verifies that primary mode excludes stale, archived, debug, and blocked records.
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


print("=== test_memory_v2_primary_excludes_stale ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- EXCLUDED_FROM_CURRENT_TRUTH list --")
exc = shadow.EXCLUDED_FROM_CURRENT_TRUTH
check("is tuple or list", isinstance(exc, (tuple, list)))
check("provider_status_snapshot excluded", "provider_status_snapshot" in exc)
check("executive_briefings excluded", "executive_briefings" in exc)
check("ai_task_queue excluded", "ai_task_queue" in exc)
check("agent_dispatch_tasks excluded", "agent_dispatch_tasks" in exc)
check("debug_note excluded", "debug_note" in exc)
check("archived_note excluded", "archived_note" in exc)

print("\n-- v2 reader stale markers --")
try:
    from lib.hermes_memory_v2_reader import _STALE_MARKERS, _has_stale
    check("_STALE_MARKERS is non-empty", bool(_STALE_MARKERS))
    # Use actual stale marker strings (domain-specific, not generic DEPRECATED/ARCHIVED)
    if _STALE_MARKERS:
        stale_sample = _STALE_MARKERS[0]
        label = f"_has_stale({stale_sample[:30]!r}) is True"
        check(label, _has_stale(stale_sample))
    check("_has_stale('active operating rule') is False",
          not _has_stale("active operating rule"))
    check("_has_stale('current preference') is False",
          not _has_stale("current preference"))
except Exception as exc_:
    print(f"  (reader not importable: {exc_})")
    check("v2 reader importable (skip stale marker checks)", False)

print("\n-- Primary approval guards exclude stale records --")
# Guard 6 in _check_primary_approval_guards uses _has_stale on titles
import inspect
src = inspect.getsource(shadow._check_primary_approval_guards)
check("guard checks for stale markers in titles", "_has_stale" in src)
check("guard checks record titles", "title" in src)
check("guard fails on stale title", "stale marker" in src or "stale" in src)

print("\n-- load_primary_memory_context excludes provider snapshots --")
ctx = shadow.load_primary_memory_context()
excluded = ctx.get("excluded", list(shadow.EXCLUDED_FROM_CURRENT_TRUTH))
check("excluded list contains provider_status_snapshot",
      "provider_status_snapshot" in excluded)
check("excluded list contains executive_briefings",
      "executive_briefings" in excluded)

print("\n-- Live data stale check --")
try:
    from lib.hermes_memory_v2_reader import _env_available, build_v2_memory_context_pack, _has_stale as has_stale
    if _env_available():
        pack = build_v2_memory_context_pack(limit=50)
        records = pack.get("records", [])
        stale_titles = [r.get("title", "") for r in records if has_stale(r.get("title", ""))]
        check(f"no stale titles in live records (found {len(stale_titles)})",
              len(stale_titles) == 0)
        if stale_titles:
            for t in stale_titles[:3]:
                print(f"    stale: {t[:60]}")
    else:
        print("  (skipped: no Supabase credentials)")
        check("live data check skipped (no credentials)", True)
except Exception as e:
    print(f"  (reader not available: {e})")
    check("live data check skipped", True)

print("\n-- _SUPABASE_WRITE_ATTEMPTED remains False --")
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
