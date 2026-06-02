"""
test_hermes_memory_v2_reader_active_live_only.py
Verifies that the v2 reader enforces status='active' AND scope='live_answer'
filters, and that excluded types/statuses are blocked at the module level.
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


print("=== test_hermes_memory_v2_reader_active_live_only ===\n")

import lib.hermes_memory_v2_reader as v2

print("-- Constants enforce active/live_answer-only reads --")
check("_VALID_STATUS == 'active'", v2._VALID_STATUS == "active")
check("_VALID_SCOPE == 'live_answer'", v2._VALID_SCOPE == "live_answer")

print("\n-- _query source code uses status and scope filters --")
src = inspect.getsource(v2._query)
check("query filters status == _VALID_STATUS", "status" in src and "_VALID_STATUS" in src)
check("query filters scope == _VALID_SCOPE", "scope" in src and "_VALID_SCOPE" in src)
check("query filters out excluded types",
      "_EXCLUDED_FROM_CURRENT_TRUTH" in src)
check("query filters out stale markers", "_has_stale" in src)

print("\n-- Excluded types blocked by load_v2_memory_by_type --")
excluded_types = [
    "provider_status_snapshot",
    "executive_briefings",
    "fallback_rule",
    "debug_note",
    "archived_note",
    "template",
]
for et in excluded_types:
    result = v2.load_v2_memory_by_type(et)
    check(f"load_v2_memory_by_type('{et}') → unavailable",
          result.get("available") is False)
    check(f"load_v2_memory_by_type('{et}') has reason",
          bool(result.get("reason")))

print("\n-- Safe types are NOT blocked by exclusion list --")
safe_types = ["operating_rule", "ray_preference", "approval_policy", "project_context",
              "lesson", "goal", "tool_registry", "scout_registry"]
for st in safe_types:
    check(f"'{st}' not in _EXCLUDED_FROM_CURRENT_TRUTH",
          st not in v2._EXCLUDED_FROM_CURRENT_TRUTH)

print("\n-- _safe_row strips dangerous fields --")
raw = {
    "memory_id": "test-001",
    "title": "Test",
    "memory_type": "lesson",
    "status": "active",
    "scope": "live_answer",
    "priority": 80,
    "confidence": 0.9,
    "tags": ["test"],
    "updated_at": "2026-06-02",
    "payload": {"secret_key": "sk-12345", "api_token": "bearer xyz"},
    "summary": "raw sensitive summary",
    "internal_notes": "private",
}
safe = v2._safe_row(raw)
check("_safe_row returns title", safe.get("title") == "Test")
check("_safe_row does NOT return payload", "payload" not in safe)
check("_safe_row does NOT return summary raw", "summary" not in safe)
check("_safe_row does NOT return internal_notes", "internal_notes" not in safe)

print("\n-- _has_stale blocks stale marker strings --")
stale_texts = [
    "Ollama OFFLINE",
    "Beehiiv pending",
    "YouTube Studio pending",
    "OpenRouter not configured",
    "Executive Memory — as of",
    "Quality escalation fallback",
    "NitroTrades",
]
for s in stale_texts:
    check(f"_has_stale detects '{s[:35]}'", v2._has_stale(s))
check("_has_stale passes clean text", not v2._has_stale("Memory Safety Contract compliance"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
