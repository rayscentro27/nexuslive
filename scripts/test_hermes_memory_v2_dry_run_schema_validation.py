"""
test_hermes_memory_v2_dry_run_schema_validation.py
Verifies that dry-run records pass Phase 4A schema validation:
valid memory_type, status, scope; integer priority; unique memory_ids;
no stale text in live_answer records; Phase 3B freshness rules intact.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

ALLOWED_MEMORY_TYPES = frozenset([
    "operating_rule", "ray_preference", "project_context", "goal",
    "tool_registry", "scout_registry", "approval_policy",
    "provider_status_snapshot", "source_intake", "action", "decision",
    "artifact", "lesson", "template", "fallback_rule", "archived_note",
    "debug_note",
])
ALLOWED_STATUSES = frozenset(["active", "archived", "deprecated", "blocked", "needs_review"])
ALLOWED_SCOPES = frozenset([
    "live_answer", "historical", "debug_only", "training", "audit", "blocked_from_telegram",
])
# Must match generator _STALE_LIVE_ANSWER_MARKERS — only actual stale status values
STALE_MARKERS = [
    "Ollama OFFLINE",
    "Beehiiv pending",
    "YouTube Studio pending",
    "OpenRouter not configured",
    "empty_safe_fallback",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_dry_run_schema_validation ===\n")

print("-- Schema validation report exists --")
val_files = sorted(MEMORY_DIR.glob("hermes_memory_v2_schema_validation_*.json"))
check("schema validation JSON report exists", len(val_files) >= 1)

if val_files:
    val = json.loads(val_files[-1].read_text(encoding="utf-8"))
    check("validation report has 'valid' field", "valid" in val)
    check("schema validation passed (0 errors)", val.get("error_count", 1) == 0)
    check("total_records >= 50", val.get("total_records", 0) >= 50)
    check("unique_memory_ids == total_records",
          val.get("unique_memory_ids", 0) == val.get("total_records", -1))

# ── Load JSONL records for direct validation ───────────────────────────────────
print("\n-- JSONL dry-run records exist --")
jsonl_files = sorted(MEMORY_DIR.glob("hermes_memory_v2_dry_run_*.jsonl"))
check("JSONL dry-run file exists", len(jsonl_files) >= 1)

if not jsonl_files:
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

records = [json.loads(l) for l in jsonl_files[-1].read_text().splitlines() if l.strip()]
check("records count >= 50", len(records) >= 50)

print("\n-- Required fields present in all records --")
required_fields = [
    "memory_id", "title", "summary", "memory_type", "status", "scope",
    "confidence", "priority", "tags", "payload", "migration_status",
    "created_at", "updated_at",
]
for field in required_fields:
    missing = [r.get("memory_id", "?") for r in records if field not in r or r[field] is None]
    check(f"field '{field}' present in all records", len(missing) == 0)

print("\n-- memory_type values are schema-valid --")
invalid_types = [(r.get("memory_id","?"), r.get("memory_type","")) for r in records
                 if r.get("memory_type") not in ALLOWED_MEMORY_TYPES]
check(f"all records have valid memory_type (found {len(invalid_types)} invalid)", len(invalid_types) == 0)
if invalid_types:
    for mid, mt in invalid_types[:3]:
        print(f"    INVALID: {mid} → {mt!r}")

print("\n-- status values are schema-valid --")
invalid_statuses = [(r.get("memory_id","?"), r.get("status","")) for r in records
                    if r.get("status") not in ALLOWED_STATUSES]
check(f"all records have valid status (found {len(invalid_statuses)} invalid)", len(invalid_statuses) == 0)

print("\n-- scope values are schema-valid --")
invalid_scopes = [(r.get("memory_id","?"), r.get("scope","")) for r in records
                  if r.get("scope") not in ALLOWED_SCOPES]
check(f"all records have valid scope (found {len(invalid_scopes)} invalid)", len(invalid_scopes) == 0)

print("\n-- priority is integer --")
non_int_priority = [r.get("memory_id","?") for r in records
                    if not isinstance(r.get("priority"), int)]
check(f"all priority values are int (found {len(non_int_priority)} non-int)", len(non_int_priority) == 0)

print("\n-- memory_id uniqueness --")
ids = [r.get("memory_id","") for r in records]
check("all memory_ids are unique", len(ids) == len(set(ids)))

print("\n-- live_answer records have no stale status values in title/summary --")
live_records = [r for r in records if r.get("scope") == "live_answer" and r.get("status") == "active"]
stale_live = []
for r in live_records:
    # Only scan title+summary — migration_notes/payload contain classification metadata
    text = " ".join([str(r.get("title","")), str(r.get("summary",""))])
    for marker in STALE_MARKERS:
        if marker.lower() in text.lower():
            stale_live.append((r.get("memory_id","?"), marker))
check(f"no stale status values in live_answer title/summary (found {len(stale_live)})", len(stale_live) == 0)

print("\n-- migration_status is dry_run for all records --")
non_dry = [r.get("memory_id","?") for r in records if r.get("migration_status") != "dry_run"]
check(f"all records have migration_status=dry_run (found {len(non_dry)} non-dry)", len(non_dry) == 0)

print("\n-- Phase 3B freshness rules still applied --")
phase3b_records = [r for r in records if r.get("payload", {}).get("phase3b_freshness_rule")]
check("at least 1 record has phase3b_freshness_rule payload", len(phase3b_records) >= 1)
tagged = [r for r in records if "phase3b_freshness" in r.get("tags", [])]
check("phase3b_freshness tag present on annotated records", len(tagged) >= 1)

print("\n-- Generator module schema constants match --")
try:
    from scripts.generate_hermes_memory_v2_dry_run import (
        ALLOWED_MEMORY_TYPES as GEN_TYPES,
        ALLOWED_STATUSES as GEN_STATUSES,
        ALLOWED_SCOPES as GEN_SCOPES,
    )
    check("generator ALLOWED_MEMORY_TYPES matches test", GEN_TYPES == ALLOWED_MEMORY_TYPES)
    check("generator ALLOWED_STATUSES matches test", GEN_STATUSES == ALLOWED_STATUSES)
    check("generator ALLOWED_SCOPES matches test", GEN_SCOPES == ALLOWED_SCOPES)
except ImportError:
    check("generator importable for constant verification", False)
    check("constants match (skipped)", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
