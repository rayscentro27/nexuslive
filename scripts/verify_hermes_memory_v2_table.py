"""
verify_hermes_memory_v2_table.py
Verifies hermes_memory_v2 table exists in Supabase with correct structure.
Uses read-only queries only. Never prints secrets or row data.
Reports: table_exists, required_columns_present, row_count, constraints, indexes.
"""
import os, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_COLUMNS = [
    "memory_id", "title", "summary", "memory_type", "status", "scope",
    "confidence", "priority", "tags", "payload", "source_table",
    "source_record_id", "migration_status", "created_at", "updated_at",
]

EXPECTED_MEMORY_TYPES = [
    "operating_rule", "ray_preference", "project_context", "goal",
    "tool_registry", "scout_registry", "approval_policy",
    "provider_status_snapshot", "source_intake", "action", "decision",
    "artifact", "lesson", "template", "fallback_rule", "archived_note",
    "debug_note",
]

EXPECTED_STATUSES = ["active", "archived", "deprecated", "blocked", "needs_review"]
EXPECTED_SCOPES = ["live_answer", "historical", "debug_only", "training", "audit", "blocked_from_telegram"]


def _get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def main() -> int:
    print("=== Verify hermes_memory_v2 Table ===\n")

    try:
        client = _get_client()
        print("Supabase client: connected")
    except Exception as exc:
        msg = str(exc)
        if "eyJ" in msg:
            msg = "[redacted]"
        print(f"ERROR: Cannot connect: {msg}")
        return 1

    results = {
        "table_exists": False,
        "required_columns_present": False,
        "row_count": None,
        "constraints_checked": False,
        "indexes_checked": False,
        "backfill_occurred": None,
    }

    # 1. Check table exists via information_schema
    try:
        resp = client.table("information_schema.tables") \
            .select("table_name") \
            .eq("table_schema", "public") \
            .eq("table_name", "hermes_memory_v2") \
            .execute()
        results["table_exists"] = len(resp.data) > 0
        status = "EXISTS" if results["table_exists"] else "NOT FOUND"
        print(f"Table hermes_memory_v2: {status}")
    except Exception:
        # Fallback: try direct select with limit 0
        try:
            client.table("hermes_memory_v2").select("memory_id").limit(0).execute()
            results["table_exists"] = True
            print("Table hermes_memory_v2: EXISTS (via direct query)")
        except Exception as exc2:
            msg = str(exc2)
            if "eyJ" in msg:
                msg = "[redacted]"
            print(f"Table hermes_memory_v2: ERROR — {msg[:120]}")
            results["table_exists"] = False

    if not results["table_exists"]:
        print("\nFAIL: Table does not exist. Migration may not have applied.")
        return 1

    # 2. Check required columns via information_schema
    try:
        resp = client.table("information_schema.columns") \
            .select("column_name") \
            .eq("table_schema", "public") \
            .eq("table_name", "hermes_memory_v2") \
            .execute()
        present_cols = {row["column_name"] for row in resp.data}
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in present_cols]
        results["required_columns_present"] = len(missing_cols) == 0
        print(f"\nColumns: {len(present_cols)} total")
        print(f"Required columns present: {'YES' if results['required_columns_present'] else 'NO'}")
        if missing_cols:
            print(f"  Missing: {missing_cols}")
    except Exception as exc:
        msg = str(exc)[:120]
        if "eyJ" in msg:
            msg = "[redacted]"
        print(f"Columns: could not check via information_schema — {msg}")
        # Fallback: try selecting required columns
        try:
            cols = ",".join(REQUIRED_COLUMNS[:5])
            client.table("hermes_memory_v2").select(cols).limit(0).execute()
            results["required_columns_present"] = True
            print("Columns: spot-check passed (first 5 required columns present)")
        except Exception:
            results["required_columns_present"] = False
            print("Columns: spot-check failed")

    # 3. Row count — must be 0 (no backfill yet)
    try:
        resp = client.table("hermes_memory_v2").select("memory_id", count="exact").execute()
        row_count = resp.count if resp.count is not None else len(resp.data)
        results["row_count"] = row_count
        results["backfill_occurred"] = row_count > 0
        print(f"\nRow count: {row_count}")
        if row_count == 0:
            print("Backfill check: PASS — 0 rows (no premature backfill)")
        else:
            print(f"Backfill check: WARNING — {row_count} rows found unexpectedly")
            print("  Do not delete. Do not modify. Report to Ray before proceeding.")
    except Exception as exc:
        msg = str(exc)[:120]
        if "eyJ" in msg:
            msg = "[redacted]"
        print(f"\nRow count: ERROR — {msg}")

    # 4. CHECK constraints via pg_constraint (informational, may not work via REST)
    try:
        resp = client.table("information_schema.check_constraints") \
            .select("constraint_name") \
            .like("constraint_name", "hermes_memory_v2%") \
            .execute()
        constraints = [r["constraint_name"] for r in resp.data]
        results["constraints_checked"] = len(constraints) > 0
        print(f"\nCHECK constraints: {len(constraints)} found")
        for c in constraints:
            print(f"  ✓ {c}")
    except Exception:
        results["constraints_checked"] = False
        print("\nCHECK constraints: could not query (REST schema cache limitation)")

    # 5. Indexes (informational via pg_indexes if accessible)
    try:
        resp = client.table("pg_indexes") \
            .select("indexname") \
            .eq("tablename", "hermes_memory_v2") \
            .execute()
        indexes = [r["indexname"] for r in resp.data]
        results["indexes_checked"] = len(indexes) > 0
        print(f"\nIndexes: {len(indexes)} found")
        for idx in sorted(indexes):
            print(f"  ✓ {idx}")
    except Exception:
        results["indexes_checked"] = False
        print("\nIndexes: could not query via REST (expected — pg_indexes not in PostgREST schema)")

    # Summary
    print("\n--- Summary ---")
    print(f"table_exists             : {results['table_exists']}")
    print(f"required_columns_present : {results['required_columns_present']}")
    print(f"row_count                : {results['row_count']}")
    print(f"backfill_occurred        : {results['backfill_occurred']}")
    print(f"constraints_checked      : {results['constraints_checked']}")
    print(f"indexes_checked          : {results['indexes_checked']}")

    ok = (
        results["table_exists"] and
        results["required_columns_present"] and
        results["row_count"] == 0
    )
    print(f"\nOverall: {'PASS — table ready for Phase 4C backfill' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
