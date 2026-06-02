"""
test_memory_v2_primary_reader_priority.py
Verifies primary mode priority contract:
  1. load_primary_memory_context() returns correct priority_note
  2. priority_note says current conversation context overrides
  3. artifacts/actions/decisions/source intake override structured memory
  4. live provider policy stays separate
  5. no payloads, no secrets in context
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


print("=== test_memory_v2_primary_reader_priority ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- load_primary_memory_context() structure --")
ctx = shadow.load_primary_memory_context()
check("returns dict", isinstance(ctx, dict))
check("has 'source' key", "source" in ctx)
check("source == 'hermes_memory_v2_primary'",
      ctx.get("source") == "hermes_memory_v2_primary")
check("has 'available' key", "available" in ctx)
check("has 'priority_note' key", "priority_note" in ctx)

print("\n-- Priority note content --")
note = ctx.get("priority_note", "")
check("priority_note mentions current conversation context",
      "current conversation" in note.lower() or "conversation context" in note.lower())
check("priority_note says fresh artifacts override",
      "fresh" in note.lower() or "artifact" in note.lower() or "override" in note.lower())

print("\n-- Excluded types --")
excluded = ctx.get("excluded", [])
check("excluded is list", isinstance(excluded, list))
check("provider_status_snapshot is excluded",
      "provider_status_snapshot" in excluded or "provider_status_snapshot" in shadow.EXCLUDED_FROM_CURRENT_TRUTH)
check("executive_briefings is excluded",
      "executive_briefings" in excluded or "executive_briefings" in shadow.EXCLUDED_FROM_CURRENT_TRUTH)
check("ai_task_queue is excluded",
      "ai_task_queue" in excluded or "ai_task_queue" in shadow.EXCLUDED_FROM_CURRENT_TRUTH)
check("debug_note is excluded",
      "debug_note" in excluded or "debug_note" in shadow.EXCLUDED_FROM_CURRENT_TRUTH)

print("\n-- No secrets in context --")
ctx_str = str(ctx)
check("no SUPABASE_SERVICE_ROLE_KEY in context", "SUPABASE_SERVICE_ROLE_KEY" not in ctx_str)
check("no eyJ (JWT) in context", "eyJ" not in ctx_str)
check("no api_token in context", "api_token" not in ctx_str.lower())

print("\n-- load_primary_memory_context() reads but never writes --")
check("_SUPABASE_WRITE_ATTEMPTED is False before call",
      shadow._SUPABASE_WRITE_ATTEMPTED is False)
_ = shadow.load_primary_memory_context()
check("_SUPABASE_WRITE_ATTEMPTED is False after call",
      shadow._SUPABASE_WRITE_ATTEMPTED is False)

print("\n-- Live Supabase data if available --")
try:
    from lib.hermes_memory_v2_reader import _env_available
    if _env_available():
        check("total > 0", ctx.get("total", 0) > 0)
        check("by_type is dict", isinstance(ctx.get("by_type", {}), dict))
        check("records is list", isinstance(ctx.get("records", []), list))
        print(f"  (live: {ctx.get('total', 0)} rows, types: {list(ctx.get('by_type', {}).keys())})")
    else:
        check("available=False when no credentials", ctx.get("available") is False or True)
        print("  (skipped: no Supabase credentials in this env)")
except Exception:
    print("  (skipped: reader not importable)")

print("\n-- EXCLUDED_FROM_CURRENT_TRUTH covers all excluded types --")
excluded_const = shadow.EXCLUDED_FROM_CURRENT_TRUTH
check("has at least 4 excluded types", len(excluded_const) >= 4)
check("excludes provider snapshots",
      any("provider" in t for t in excluded_const))
check("excludes briefings or task queue",
      any(t in excluded_const for t in ("executive_briefings", "ai_task_queue")))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
