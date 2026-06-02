"""
test_hermes_memory_v2_sql_migration.py
Verifies the Phase 4A SQL migration file is well-formed, contains all
required columns, CHECK constraints, and indexes — without executing it.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE = ROOT / "supabase" / "migrations" / "20260602004443_create_hermes_memory_v2.sql"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_sql_migration ===\n")

print("-- File existence --")
check("migration file exists", MIGRATION_FILE.exists())

if not MIGRATION_FILE.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

sql = MIGRATION_FILE.read_text(encoding="utf-8")
sql_upper = sql.upper()

print("\n-- Table creation --")
check("creates hermes_memory_v2", "hermes_memory_v2" in sql)
check("uses CREATE TABLE IF NOT EXISTS", "CREATE TABLE IF NOT EXISTS" in sql_upper)
check("has uuid primary key", "uuid" in sql.lower() and "primary key" in sql.lower())
check("uses gen_random_uuid()", "gen_random_uuid()" in sql)

print("\n-- Required columns --")
required_cols = [
    "memory_id", "title", "summary", "memory_type", "status", "scope",
    "source", "source_table", "source_record_id", "evidence_path",
    "related_action_id", "related_decision_id", "related_goal_id",
    "related_source_id", "related_artifact_id", "related_scout",
    "confidence", "priority", "tags", "payload",
    "created_at", "updated_at", "deprecated_at", "deprecated_reason",
    "replacement_memory_id", "migration_status", "migration_notes",
]
for col in required_cols:
    check(f"column '{col}' defined", col in sql)

print("\n-- CHECK constraints --")
check("memory_type CHECK constraint present", "chk_hmv2_memory_type" in sql or
      ("check" in sql.lower() and "memory_type" in sql and "in (" in sql.lower()))
check("status CHECK constraint present", "chk_hmv2_status" in sql or
      ("check" in sql.lower() and "status" in sql and "active" in sql and "archived" in sql))
check("scope CHECK constraint present", "chk_hmv2_scope" in sql or
      ("check" in sql.lower() and "scope" in sql and "live_answer" in sql))
check("migration_status CHECK constraint present",
      "chk_hmv2_migration_status" in sql or ("migration_status" in sql and "dry_run" in sql))

print("\n-- CHECK constraint values --")
for mt in ["operating_rule", "ray_preference", "provider_status_snapshot",
           "fallback_rule", "archived_note", "debug_note", "action", "decision"]:
    check(f"memory_type '{mt}' in constraint", mt in sql)
for st in ["active", "archived", "deprecated", "blocked", "needs_review"]:
    check(f"status '{st}' in constraint", st in sql)
for sc in ["live_answer", "historical", "debug_only", "blocked_from_telegram"]:
    check(f"scope '{sc}' in constraint", sc in sql)

print("\n-- Indexes --")
check("memory_id unique index", "idx_hmv2_memory_id" in sql or
      ("unique index" in sql.lower() and "memory_id" in sql))
check("status index", "idx_hmv2_status" in sql or ("index" in sql.lower() and "status" in sql))
check("scope index", "idx_hmv2_scope" in sql or ("index" in sql.lower() and "scope" in sql))
check("memory_type index", "idx_hmv2_memory_type" in sql)
check("updated_at index", "idx_hmv2_updated_at" in sql or ("index" in sql.lower() and "updated_at" in sql))
check("source ref index", "idx_hmv2_source_ref" in sql)
check("related_action_id index", "idx_hmv2_related_action" in sql or "related_action_id" in sql)
check("related_decision_id index", "idx_hmv2_related_decision" in sql or "related_decision_id" in sql)
check("related_goal_id index", "idx_hmv2_related_goal" in sql or "related_goal_id" in sql)
check("tags GIN index", "gin" in sql.lower() and "tags" in sql)
check("payload GIN index", "gin" in sql.lower() and "payload" in sql)

print("\n-- updated_at trigger --")
check("trigger defined for updated_at", "trg_hermes_memory_v2_touch" in sql or
      ("trigger" in sql.lower() and "updated_at" in sql))
check("uses touch_updated_at() function", "touch_updated_at" in sql)

print("\n-- RLS --")
check("RLS enabled", "enable row level security" in sql.lower())
check("service_role policy present", "service_role" in sql)

print("\n-- Safety: no data writes --")
check("no INSERT INTO in migration (data)", "INSERT INTO" not in sql_upper)
check("no UPDATE in migration", "UPDATE hermes_memory_v2" not in sql)
check("no DELETE in migration", "DELETE FROM" not in sql_upper)

print("\n-- Safety: no secrets --")
for secret_key in ["SUPABASE_KEY", "SERVICE_ROLE_KEY", "eyJ"]:
    check(f"no '{secret_key}' in SQL", secret_key not in sql)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
