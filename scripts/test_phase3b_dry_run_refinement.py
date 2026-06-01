"""
test_phase3b_dry_run_refinement.py
Verifies that the Phase 3B dry-run generator correctly annotates records
with freshness rules and produces the expected phase3b reports.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

PASS = 0; FAIL = 0

PHASE3B_TABLES = frozenset([
    "provider_health",
    "executive_briefings",
    "hermes_conversation_context",
    "ai_task_queue",
    "agent_dispatch_tasks",
    "nexus_skills",
])


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_phase3b_dry_run_refinement ===\n")

# ── Phase 3B report files exist ───────────────────────────────────────────────
print("-- Phase 3B report files exist --")
phase3b_json_files = sorted(MEMORY_DIR.glob("phase3b_stale_safety_refinement_*.json"))
phase3b_md_files   = sorted(MEMORY_DIR.glob("phase3b_stale_safety_refinement_*.md"))

check("phase3b JSON report exists", len(phase3b_json_files) >= 1)
check("phase3b MD report exists",   len(phase3b_md_files) >= 1)

if not phase3b_json_files:
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

# ── Phase 3B JSON structure ───────────────────────────────────────────────────
print("\n-- Phase 3B JSON structure --")
data = json.loads(phase3b_json_files[-1].read_text(encoding="utf-8"))

check("phase == '3B'", data.get("phase") == "3B")
check("supabase_write_attempted == False", data.get("supabase_write_attempted") == False)
check("affected_tables present", "affected_tables" in data)
check("rules present", "rules" in data)
check("annotated_records_count >= 1", data.get("annotated_records_count", 0) >= 1)
check("total_records_count >= 50", data.get("total_records_count", 0) >= 50)

# ── Affected tables coverage ──────────────────────────────────────────────────
print("\n-- Affected tables in report --")
affected = set(data.get("affected_tables", []))
for table in PHASE3B_TABLES:
    check(f"'{table}' in affected_tables", table in affected)

# ── Freshness rules for each table ───────────────────────────────────────────
print("\n-- Freshness rules defined for each affected table --")
rules = data.get("rules", {})
for table in PHASE3B_TABLES:
    check(f"rule defined for '{table}'", table in rules)

check("provider_health rule has max_age_minutes",
      "max_age_minutes" in rules.get("provider_health", {}))
check("provider_health rule has stale_values",
      "stale_values" in rules.get("provider_health", {}))
check("executive_briefings rule has max_age_hours",
      "max_age_hours" in rules.get("executive_briefings", {}))
check("hermes_conversation_context rule has max_age_hours",
      "max_age_hours" in rules.get("hermes_conversation_context", {}))
check("ai_task_queue rule has active_statuses",
      "active_statuses" in rules.get("ai_task_queue", {}))
check("nexus_skills rule has active_statuses",
      "active_statuses" in rules.get("nexus_skills", {}))

# ── Annotated records ─────────────────────────────────────────────────────────
print("\n-- Annotated records --")
annotated = data.get("annotated_records", [])
check("at least 1 annotated record", len(annotated) >= 1)
if annotated:
    first = annotated[0]
    check("annotated record has memory_id", "memory_id" in first)
    check("annotated record has title", "title" in first)
    check("annotated record has status", "status" in first)
    check("annotated record has freshness_rule", "freshness_rule" in first)
    check("freshness_rule is non-empty dict", isinstance(first.get("freshness_rule"), dict) and len(first["freshness_rule"]) > 0)

# ── Generator output: jsonl records have phase3b payload ─────────────────────
print("\n-- JSONL dry-run records include phase3b payload --")
jsonl_files = sorted(MEMORY_DIR.glob("hermes_memory_v2_dry_run_*.jsonl"))
if jsonl_files:
    records = [json.loads(l) for l in jsonl_files[-1].read_text().splitlines() if l.strip()]
    phase3b_records = [r for r in records if r.get("payload", {}).get("phase3b_freshness_rule")]
    check("at least 1 record has phase3b_freshness_rule payload", len(phase3b_records) >= 1)
    check("all records have migration_status=dry_run",
          all(r.get("migration_status") == "dry_run" for r in records))
    check("all records have 'dry_run' in migration_notes (spot-check first 5)",
          all("dry_run" in r.get("migration_notes", "").lower() or "dry-run" in r.get("migration_notes", "").lower()
              for r in records[:5]))

    # Verify records tagged with phase3b_freshness have the correct tag
    tagged_records = [r for r in records if "phase3b_freshness" in r.get("tags", [])]
    check("phase3b_freshness tag present on annotated records", len(tagged_records) >= 1)

# ── Generator has no Supabase write calls ─────────────────────────────────────
print("\n-- Generator has no Supabase writes (re-verify after Phase 3B update) --")
gen_src = (ROOT / "scripts" / "generate_hermes_memory_v2_dry_run.py").read_text()
check("no 'INSERT INTO' in generator", "INSERT INTO" not in gen_src.upper())
check("no '.post(' in generator", ".post(" not in gen_src)
check("no '.patch(' in generator", ".patch(" not in gen_src)
check("_SUPABASE_WRITE_ATTEMPTED sentinel present", "_SUPABASE_WRITE_ATTEMPTED" in gen_src)
check("sentinel initialized to False", "_SUPABASE_WRITE_ATTEMPTED = False" in gen_src)

# ── hermes_memory_freshness module loadable ───────────────────────────────────
print("\n-- hermes_memory_freshness module --")
try:
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from lib.hermes_memory_freshness import (
        classify_provider_health_record,
        classify_executive_briefing,
        classify_conversation_context,
        classify_task_record,
        classify_nexus_skill,
        classify_record,
        is_context_fresh,
        stale_context_clarification,
    )
    check("hermes_memory_freshness importable", True)
    check("all 8 key functions present", True)
except ImportError as e:
    check(f"hermes_memory_freshness importable: {e}", False)
    check("all 8 key functions present", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
