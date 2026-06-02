"""
test_compare_memory_v2_after_batch2.py
Verifies that 'compare memory v2' no longer shows Batch 2 types as missing
and correctly shows all 8 planned types as present (when credentials available).
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env credentials if available so live Supabase checks work
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


print("=== test_compare_memory_v2_after_batch2 ===\n")

from lib.hermes_memory_v2_reader import compare_v2_with_current_memory
from hermes_command_router.router import run_command

PLANNED_TYPES = ["operating_rule", "ray_preference", "approval_policy", "project_context",
                 "lesson", "goal", "tool_registry", "scout_registry"]
BATCH2_TYPES  = ["lesson", "goal", "tool_registry", "scout_registry"]

cmp = compare_v2_with_current_memory()
v2_available = cmp.get("v2_available", False)

print(f"-- v2 available in this env: {v2_available} --")
if v2_available:
    print("   (live Supabase credentials present — running live checks)")
else:
    print("   (credentials not in env — running structural checks only)")

print("\n-- compare_v2_with_current_memory: Batch 2 types not missing when v2 available --")
if v2_available:
    check("missing_from_v2 is empty list", cmp.get("missing_from_v2") == [])
    for bt in BATCH2_TYPES:
        check(f"'{bt}' NOT in missing_from_v2", bt not in cmp.get("missing_from_v2", []))
    for pt in PLANNED_TYPES:
        check(f"'{pt}' present in v2_by_type", cmp.get("v2_by_type", {}).get(pt, 0) > 0)
    check("recommendation says 'Batch 2 applied' or 'coverage complete'",
          "batch 2 applied" in cmp.get("recommendation", "").lower() or
          "coverage complete" in cmp.get("recommendation", "").lower() or
          "shadow" in cmp.get("recommendation", "").lower())
else:
    # Without credentials, missing_from_v2 is computed from empty v2 — acceptable
    check("missing_from_v2 is a list", isinstance(cmp.get("missing_from_v2"), list))
    print("   SKIP live data checks (no credentials)")

print("\n-- response structure: new sections present (credential-independent) --")
result = run_command("compare memory v2", source="telegram") or ""
check("response non-empty", bool(result.strip()))
check("response has 'MEMORY READER COMPARISON' header", "MEMORY READER COMPARISON" in result)
check("response has 'Planned Batch 1/2 coverage' section",
      "Planned Batch 1/2 coverage" in result)
check("response has 'Missing from planned Batch 1/2' section",
      "Missing from planned Batch 1/2" in result)
check("response has 'Still excluded from current-truth memory' section",
      "Still excluded from current-truth memory" in result)
check("response has 'Recommendation:' label", "Recommendation:" in result)

print("\n-- old incorrect section headers are gone --")
check("no 'Missing from v2 (Batch 2 targets)' header",
      "Missing from v2 (Batch 2 targets)" not in result)
check("no 'Extra in v2 (not in current reader):' standalone header",
      "Extra in v2 (not in current reader):" not in result)

print("\n-- coverage section shows correct structure --")
for pt in PLANNED_TYPES:
    check(f"coverage section has '{pt}:' entry",
          f"- {pt}:" in result)

print("\n-- excluded types section is present --")
for et in ["provider_status_snapshot", "executive_briefings", "fallback_rule"]:
    check(f"excluded section contains '{et}'", et in result)

print("\n-- recommendation is appropriate --")
rec_present = "Recommendation:" in result
if rec_present:
    rec_idx = result.index("Recommendation:")
    rec_text = result[rec_idx:rec_idx + 200].lower()
    check("recommendation mentions shadow or primary",
          "shadow" in rec_text or "primary" in rec_text)

print("\n-- live data check when v2 available --")
if v2_available:
    check("coverage section shows all 8 types as 'present'",
          all(f"- {pt}: present" in result for pt in PLANNED_TYPES))
    check("'Missing from planned Batch 1/2' says '- none'",
          "- none" in result)
else:
    print("   SKIP (no Supabase credentials in this env)")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
