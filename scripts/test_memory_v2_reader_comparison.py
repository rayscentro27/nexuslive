"""
test_memory_v2_reader_comparison.py
Verifies the compare_v2_with_current_memory function and the comparison script
produce the expected output structure without switching readers.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_reader_comparison ===\n")

from lib.hermes_memory_v2_reader import compare_v2_with_current_memory

print("-- compare_v2_with_current_memory structure --")
cmp = compare_v2_with_current_memory()
check("returns dict", isinstance(cmp, dict))
required_keys = ["current_available", "current_sources", "v2_available", "v2_total",
                 "v2_by_type", "overlap", "extra_in_v2", "missing_from_v2", "recommendation"]
for key in required_keys:
    check(f"has '{key}' key", key in cmp)

check("current_sources is list", isinstance(cmp.get("current_sources"), list))
check("current_sources non-empty", len(cmp.get("current_sources", [])) > 0)
check("v2_by_type is dict", isinstance(cmp.get("v2_by_type"), dict))
check("missing_from_v2 is list", isinstance(cmp.get("missing_from_v2"), list))
check("recommendation is str", isinstance(cmp.get("recommendation"), str))
check("recommendation mentions preview",
      "preview" in cmp.get("recommendation", "").lower())
check("recommendation does NOT say switch now",
      "switch to v2" not in cmp.get("recommendation", "").lower() or
      ("after" in cmp.get("recommendation", "").lower() and "approval" in cmp.get("recommendation", "").lower()))

print("\n-- Batch 2 types listed as missing_from_v2 --")
batch2_types = {"lesson", "goal", "tool_registry", "scout_registry"}
missing = set(cmp.get("missing_from_v2", []))
for bt in batch2_types:
    check(f"'{bt}' in missing_from_v2", bt in missing)

print("\n-- compare script output report exists --")
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"
comparison_reports = list(MEMORY_DIR.glob("phase4d_reader_comparison_*.json"))
check("reader comparison report was generated", len(comparison_reports) > 0)
if comparison_reports:
    latest = max(comparison_reports, key=lambda p: p.stat().st_mtime)
    report = json.loads(latest.read_text())
    check("report has 'supabase_writes_attempted': False",
          report.get("supabase_writes_attempted") is False)
    check("report has 'live_reader_switched': False",
          report.get("live_reader_switched") is False)
    check("report has 'recommendation'", bool(report.get("recommendation")))
    check("report has 'current_sources'", bool(report.get("current_sources")))

print("\n-- compare command via run_command --")
from hermes_command_router.router import run_command
result = run_command("compare memory v2", source="telegram") or ""
check("'compare memory v2' returns non-empty", bool(result.strip()))
check("response contains 'MEMORY READER COMPARISON'", "MEMORY READER COMPARISON" in result)
check("response contains 'Current reader'", "Current reader:" in result)
check("response contains 'Memory v2 preview'", "Memory v2 preview:" in result)
check("response contains 'Recommendation'", "Recommendation:" in result)
check("response no stale Executive Memory",
      "Executive Memory — as of" not in result)
check("response no evidence dump", "[artifact_inventory]" not in result)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
