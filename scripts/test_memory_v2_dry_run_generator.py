"""
test_memory_v2_dry_run_generator.py
Verifies the dry-run generator produces correct records and does NOT write to Supabase.
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

print("=== test_memory_v2_dry_run_generator ===\n")

# Import and run generator in-process
sys.path.insert(0, str(ROOT))
from scripts.generate_hermes_memory_v2_dry_run import generate_records, _SUPABASE_WRITE_ATTEMPTED

# ── Generator produces records ─────────────────────────────────────────────
print("-- Record generation --")
records = generate_records()
check("generates at least 50 records", len(records) >= 50)
check("no Supabase write attempted", not _SUPABASE_WRITE_ATTEMPTED)

# ── Required fields ────────────────────────────────────────────────────────
print("\n-- Required fields in every record --")
required = [
    "memory_id", "title", "summary", "memory_type", "status", "scope",
    "source", "source_table", "source_path", "source_record_id",
    "evidence_path", "related_action_id", "related_decision_id",
    "related_goal_id", "related_source_id", "related_artifact_id",
    "related_scout", "confidence", "priority", "tags", "payload",
    "migration_status", "migration_notes", "deprecated_reason",
    "replacement_memory_id"
]
for field in required:
    check(f"all records have '{field}'", all(field in r for r in records))

# ── Status values ─────────────────────────────────────────────────────────
print("\n-- Status values valid --")
allowed_statuses = {"active", "archived", "deprecated", "blocked", "needs_review"}
check("all statuses are valid", all(r["status"] in allowed_statuses for r in records))

allowed_scopes = {"live_answer", "historical", "debug_only", "training", "audit", "blocked_from_telegram"}
check("all scopes are valid", all(r["scope"] in allowed_scopes for r in records))

# ── Blocked records ────────────────────────────────────────────────────────
print("\n-- Blocked records --")
blocked = [r for r in records if r["status"] == "blocked"]
check("at least 2 blocked records", len(blocked) >= 2)
check("blocked records have blocked_from_telegram scope",
      all(r["scope"] == "blocked_from_telegram" for r in blocked))

# ── Deprecated records ─────────────────────────────────────────────────────
print("\n-- Deprecated records --")
deprecated = [r for r in records if r["status"] == "deprecated"]
check("at least 1 deprecated record", len(deprecated) >= 1)

# ── Migration status ───────────────────────────────────────────────────────
print("\n-- Migration status --")
check("all records have migration_status=dry_run",
      all(r["migration_status"] == "dry_run" for r in records))

# ── No secrets in records ─────────────────────────────────────────────────
print("\n-- No secrets in records --")
SECRET_PATTERNS = ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY", "OPENAI_API_KEY",
                   "OPENROUTER", "ANTHROPIC", "OANDA", "PASSWORD", "SECRET", "PRIVATE_KEY"]
all_text = json.dumps(records)
for p in SECRET_PATTERNS:
    check(f"no secret '{p}' in records", p not in all_text)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
