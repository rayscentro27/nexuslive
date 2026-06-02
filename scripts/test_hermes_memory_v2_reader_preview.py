"""
test_hermes_memory_v2_reader_preview.py
Verifies the hermes_memory_v2_reader module: functions exist, return correct
structure when credentials are unavailable, and preview-only mode is enforced.
"""
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_reader_preview ===\n")

import lib.hermes_memory_v2_reader as v2_reader

print("-- Module structure --")
check("_SUPABASE_WRITE_ATTEMPTED is False",
      v2_reader._SUPABASE_WRITE_ATTEMPTED is False)
check("_EXCLUDED_FROM_CURRENT_TRUTH defined",
      bool(v2_reader._EXCLUDED_FROM_CURRENT_TRUTH))
check("provider_status_snapshot excluded",
      "provider_status_snapshot" in v2_reader._EXCLUDED_FROM_CURRENT_TRUTH)
check("executive_briefings excluded",
      "executive_briefings" in v2_reader._EXCLUDED_FROM_CURRENT_TRUTH)
check("fallback_rule excluded",
      "fallback_rule" in v2_reader._EXCLUDED_FROM_CURRENT_TRUTH)
check("debug_note excluded",
      "debug_note" in v2_reader._EXCLUDED_FROM_CURRENT_TRUTH)

print("\n-- Required functions defined --")
required_fns = [
    "load_v2_active_live_answer_memory",
    "load_v2_operating_rules",
    "load_v2_ray_preferences",
    "load_v2_approval_policies",
    "load_v2_project_context",
    "load_v2_memory_by_type",
    "build_v2_memory_context_pack",
    "compare_v2_with_current_memory",
    "explain_v2_reader_status",
]
for fn in required_fns:
    check(f"function '{fn}' exists", hasattr(v2_reader, fn))

print("\n-- Functions return correct structure when credentials unavailable --")
result = v2_reader.load_v2_active_live_answer_memory()
check("load_v2_active_live_answer_memory returns dict", isinstance(result, dict))
check("has 'available' key", "available" in result)
check("has 'records' key", "records" in result)
check("records is list", isinstance(result.get("records"), list))
check("has 'reason' key", "reason" in result)

result_op = v2_reader.load_v2_operating_rules()
check("load_v2_operating_rules returns dict", isinstance(result_op, dict))
check("has 'available' key", "available" in result_op)

result_pack = v2_reader.build_v2_memory_context_pack()
check("build_v2_memory_context_pack returns dict", isinstance(result_pack, dict))
check("has 'by_type' key", "by_type" in result_pack)
check("by_type is dict", isinstance(result_pack.get("by_type"), dict))

print("\n-- explain_v2_reader_status returns preview-only text --")
status_text = v2_reader.explain_v2_reader_status()
check("explain_v2_reader_status returns str", isinstance(status_text, str))
check("contains HERMES MEMORY V2 STATUS header",
      "HERMES MEMORY V2 STATUS" in status_text)
check("mentions preview only / not primary",
      "preview" in status_text.lower() or "not" in status_text.lower())
check("does not claim v2 is live primary reader",
      "primary reader" not in status_text.lower() or
      ("not" in status_text.lower() and "primary" in status_text.lower()))

print("\n-- compare_v2_with_current_memory returns comparison dict --")
cmp = v2_reader.compare_v2_with_current_memory()
check("returns dict", isinstance(cmp, dict))
check("has 'current_sources' key", "current_sources" in cmp)
check("has 'v2_available' key", "v2_available" in cmp)
check("has 'recommendation' key", "recommendation" in cmp)
check("has 'missing_from_v2' key", "missing_from_v2" in cmp)
check("recommendation contains 'preview'",
      "preview" in cmp.get("recommendation", "").lower())

print("\n-- load_v2_memory_by_type blocks excluded types --")
blocked = v2_reader.load_v2_memory_by_type("provider_status_snapshot")
check("provider_status_snapshot returns unavailable",
      blocked.get("available") is False)
check("reason mentions excluded", "excluded" in blocked.get("reason", "").lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
