"""
test_memory_source_map_exists.py
Verifies Phase 3 audit reports exist and have expected structure.
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

print("=== test_memory_source_map_exists ===\n")

# ── Reports exist ─────────────────────────────────────────────────────────────
print("-- Report files exist --")
check("memory dir exists", MEMORY_DIR.exists())
check("source map md exists", len(list(MEMORY_DIR.glob("hermes_memory_source_map_*.md"))) > 0)
check("source map json exists", len(list(MEMORY_DIR.glob("hermes_memory_source_map_*.json"))) > 0)
check("supabase classification md exists", len(list(MEMORY_DIR.glob("supabase_table_memory_classification_*.md"))) > 0)
check("supabase classification json exists", len(list(MEMORY_DIR.glob("supabase_table_memory_classification_*.json"))) > 0)
check("local classification md exists", len(list(MEMORY_DIR.glob("local_memory_classification_*.md"))) > 0)
check("local classification json exists", len(list(MEMORY_DIR.glob("local_memory_classification_*.json"))) > 0)
check("fallback audit md exists", len(list(MEMORY_DIR.glob("fallback_response_pattern_audit_*.md"))) > 0)
check("fallback audit json exists", len(list(MEMORY_DIR.glob("fallback_response_pattern_audit_*.json"))) > 0)
check("classification rules doc exists", (ROOT / "docs" / "HERMES_MEMORY_CLASSIFICATION_RULES.md").exists())
check("phase3 summary exists", len(list(MEMORY_DIR.glob("phase3_memory_classification_dry_run_summary_*.md"))) > 0)
check("dry-run generator exists", (ROOT / "scripts" / "generate_hermes_memory_v2_dry_run.py").exists())
check("dry-run jsonl exists", len(list(MEMORY_DIR.glob("hermes_memory_v2_dry_run_*.jsonl"))) > 0)
check("dry-run md exists", len(list(MEMORY_DIR.glob("hermes_memory_v2_dry_run_*.md"))) > 0)

# ── Source map JSON structure ─────────────────────────────────────────────────
print("\n-- Source map JSON structure --")
src_map_files = sorted(MEMORY_DIR.glob("hermes_memory_source_map_*.json"))
if src_map_files:
    data = json.loads(src_map_files[-1].read_text())
    check("has report_metadata", "report_metadata" in data)
    check("data_changed is false", data.get("report_metadata", {}).get("data_changed") == False)
    check("has summary", "summary" in data)
    check("has supabase_tables", "supabase_tables" in data)
    check("has local_files", "local_files" in data)
    check("has code_fallbacks", "code_fallbacks" in data)
    check("supabase_tables is list", isinstance(data["supabase_tables"], list))
    check("supabase_tables has entries", len(data["supabase_tables"]) > 0)
    check("each table has source_id", all("source_id" in t for t in data["supabase_tables"]))
    check("each table has classification", all("classification" in t for t in data["supabase_tables"]))

# ── Dry-run JSONL structure ────────────────────────────────────────────────────
print("\n-- Dry-run JSONL records --")
jsonl_files = sorted(MEMORY_DIR.glob("hermes_memory_v2_dry_run_*.jsonl"))
if jsonl_files:
    records = [json.loads(l) for l in jsonl_files[-1].read_text().splitlines() if l.strip()]
    check("at least 50 records generated", len(records) >= 50)
    required_fields = ["memory_id", "title", "status", "scope", "memory_type",
                       "source", "migration_status", "migration_notes"]
    for field in required_fields:
        check(f"records have '{field}' field", all(field in r for r in records))
    check("migration_status is dry_run for all", all(r.get("migration_status") == "dry_run" for r in records))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
