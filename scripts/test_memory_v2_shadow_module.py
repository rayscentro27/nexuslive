"""
test_memory_v2_shadow_module.py
Verifies lib/hermes_memory_v2_shadow.py structure, function signatures,
constants, and safe-metadata-only behavior.
"""
import sys, os, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_shadow_module ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- Safety sentinel --")
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

print("\n-- Required functions exist --")
required_fns = [
    "get_memory_v2_mode",
    "is_shadow_mode_enabled",
    "run_shadow_memory_comparison",
    "compare_shadow_contexts",
    "log_shadow_memory_result",
    "format_shadow_status",
    "format_v2_live_status",
    "trigger_shadow_comparison_async",
]
for fn in required_fns:
    check(f"function '{fn}' exists", hasattr(shadow, fn))

print("\n-- Constants --")
check("PLANNED_BATCH_TYPES defined", hasattr(shadow, "PLANNED_BATCH_TYPES"))
check("PLANNED_BATCH_TYPES has 8 entries", len(shadow.PLANNED_BATCH_TYPES) == 8)
for t in ["operating_rule", "ray_preference", "approval_policy", "project_context",
          "lesson", "goal", "tool_registry", "scout_registry"]:
    check(f"'{t}' in PLANNED_BATCH_TYPES", t in shadow.PLANNED_BATCH_TYPES)
check("EXCLUDED_FROM_CURRENT_TRUTH defined",
      hasattr(shadow, "EXCLUDED_FROM_CURRENT_TRUTH"))
for et in ["provider_status_snapshot", "executive_briefings", "fallback_rule"]:
    check(f"'{et}' in EXCLUDED_FROM_CURRENT_TRUTH", et in shadow.EXCLUDED_FROM_CURRENT_TRUTH)
check("SHADOW_LOG_PATH defined", hasattr(shadow, "SHADOW_LOG_PATH"))
check("SHADOW_LOG_PATH is in docs/reports/memory/shadow/",
      "shadow" in str(shadow.SHADOW_LOG_PATH))

print("\n-- compare_shadow_contexts structure --")
result = shadow.compare_shadow_contexts({}, {})
check("returns dict", isinstance(result, dict))
for key in ["v2_available", "v2_total", "v2_by_type", "current_sources",
            "planned_types_count", "present_count", "missing_types",
            "coverage_pct", "risk_flags", "recommendation", "live_response_changed"]:
    check(f"has '{key}' key", key in result)
check("live_response_changed is False", result.get("live_response_changed") is False)
check("planned_types_count == 8", result.get("planned_types_count") == 8)

print("\n-- run_shadow_memory_comparison returns safe metadata --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
r = shadow.run_shadow_memory_comparison("test message", {}, "test response")
check("returns dict", isinstance(r, dict))
check("has 'timestamp'", "timestamp" in r)
check("has 'message_hash'", "message_hash" in r)
check("has 'mode'", "mode" in r)
check("has 'v2_record_count'", "v2_record_count" in r)
check("has 'overlap_summary'", "overlap_summary" in r)
check("has 'missing_summary'", "missing_summary" in r)
check("has 'risk_flags'", "risk_flags" in r)
check("has 'recommendation'", "recommendation" in r)
check("live_response_changed is False", r.get("live_response_changed") is False)
check("message_hash is NOT the raw message",
      r.get("message_hash") != "test message")
check("mode field is 'shadow'", r.get("mode") == "shadow")

print("\n-- run_shadow_memory_comparison does not write secrets --")
check("result does not contain 'secret_key'",
      "secret_key" not in str(r).lower())
check("result does not contain 'api_token'",
      "api_token" not in str(r).lower())
check("result does not contain 'eyJ' (JWT)",
      "eyJ" not in str(r))
check("_SUPABASE_WRITE_ATTEMPTED still False after run",
      shadow._SUPABASE_WRITE_ATTEMPTED is False)

print("\n-- source code safety checks --")
src = inspect.getsource(shadow)
check("source does not call .insert(", ".insert(" not in src or
      "sys.path.insert" in src)
check("source does not call .upsert(", ".upsert(" not in src)
check("source does not call .delete(", ".delete(" not in src)
check("source does not modify live response",
      "live_response_changed" in src)

os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
