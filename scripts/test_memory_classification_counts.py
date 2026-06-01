"""
test_memory_classification_counts.py
Verifies that the Phase 3 source map has expected classification count thresholds.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

PASS = 0; FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")

print("=== test_memory_classification_counts ===\n")

# Load source map
src_files = sorted(MEMORY_DIR.glob("hermes_memory_source_map_*.json"))
if not src_files:
    check("source map JSON exists", False)
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

data = json.loads(src_files[-1].read_text())
summary = data.get("summary", {})

print("-- Summary counts --")
check("total_sources >= 50", summary.get("total_sources", 0) >= 50)
check("active_live_answer >= 25", summary.get("active_live_answer", 0) >= 25)
check("historical_only >= 10", summary.get("historical_only", 0) >= 10)
check("blocked_from_live >= 2", summary.get("blocked_from_live", 0) >= 2)
check("needs_review >= 1", summary.get("needs_review", 0) >= 1)

# Classification distribution check
print("\n-- Classification distribution in tables --")
tables = data.get("supabase_tables", [])
active_tables = [t for t in tables if t.get("classification") == "active_live_answer"]
blocked_tables = [t for t in tables if t.get("classification") == "blocked_from_live"]
historical_tables = [t for t in tables if t.get("classification") == "historical_only"]
needs_review_tables = [t for t in tables if t.get("classification") == "needs_review"]

check("at least 10 active_live_answer Supabase tables", len(active_tables) >= 10)
check("at least 5 historical_only Supabase tables", len(historical_tables) >= 5)
check("at least 3 needs_review Supabase tables", len(needs_review_tables) >= 3)

# hermes_executive_memory must be listed as active_live_answer (via active_reader)
exec_mem_table = next((t for t in tables if t.get("table") == "hermes_executive_memory"), None)
check("hermes_executive_memory table found", exec_mem_table is not None)
if exec_mem_table:
    check("hermes_executive_memory classified active_live_answer",
          exec_mem_table.get("classification") == "active_live_answer")
    check("hermes_executive_memory noted as high risk",
          exec_mem_table.get("risk") in ("high", "critical"))

# Code fallbacks: blocked count
print("\n-- Code fallback counts --")
fallbacks = data.get("code_fallbacks", [])
blocked_fb = [f for f in fallbacks if f.get("classification") in ("blocked_from_live", "deprecated")]
active_fb = [f for f in fallbacks if f.get("classification") == "active_live_answer"]
check("at least 2 blocked/deprecated fallbacks", len(blocked_fb) >= 2)
check("at least 6 active_live_answer fallbacks", len(active_fb) >= 6)

# Dry-run records
print("\n-- Dry-run records --")
jsonl_files = sorted(MEMORY_DIR.glob("hermes_memory_v2_dry_run_*.jsonl"))
if jsonl_files:
    records = [json.loads(l) for l in jsonl_files[-1].read_text().splitlines() if l.strip()]
    blocked_records = [r for r in records if r.get("status") == "blocked"]
    deprecated_records = [r for r in records if r.get("status") == "deprecated"]
    check("dry-run has blocked records", len(blocked_records) > 0)
    check("dry-run has deprecated records", len(deprecated_records) > 0)
    check("dry-run all migration_status=dry_run",
          all(r.get("migration_status") == "dry_run" for r in records))
else:
    check("dry-run jsonl exists", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
