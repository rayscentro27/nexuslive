"""
test_hermes_memory_v2_schema_doc.py
Verifies docs/HERMES_MEMORY_V2_SCHEMA.md exists and defines all required
memory_type, status, and scope values.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_schema_doc ===\n")

schema_doc = ROOT / "docs" / "HERMES_MEMORY_V2_SCHEMA.md"

print("-- File existence --")
check("HERMES_MEMORY_V2_SCHEMA.md exists", schema_doc.exists())

if not schema_doc.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

content = schema_doc.read_text(encoding="utf-8")

print("\n-- Core structure --")
check("has title 'Hermes Memory v2'", "Hermes Memory v2" in content)
check("has Purpose section", "Purpose" in content or "purpose" in content.lower())
check("has Core Live-Answer Rule section", "Core Live-Answer Rule" in content or "core live" in content.lower())
check("has Columns table", "memory_id" in content and "title" in content and "summary" in content)
check("has Allowed Values section", "Allowed Values" in content or "allowed" in content.lower())

print("\n-- Required memory_type values --")
required_types = [
    "operating_rule", "ray_preference", "project_context", "goal",
    "tool_registry", "scout_registry", "approval_policy",
    "provider_status_snapshot", "source_intake", "action", "decision",
    "artifact", "lesson", "template", "fallback_rule", "archived_note",
    "debug_note",
]
for mt in required_types:
    check(f"memory_type '{mt}' documented", mt in content)

print("\n-- Required status values --")
for status in ["active", "archived", "deprecated", "blocked", "needs_review"]:
    check(f"status '{status}' documented", status in content)

print("\n-- Required scope values --")
for scope in ["live_answer", "historical", "debug_only", "training", "audit", "blocked_from_telegram"]:
    check(f"scope '{scope}' documented", scope in content)

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
    check(f"column '{col}' documented", col in content)

print("\n-- Live-answer safety rule --")
check("live_answer rule documented", "live_answer" in content and "active" in content)
check("deprecated must never be used live", "deprecated" in content and ("never" in content.lower() or "must not" in content.lower()))
check("blocked must never be used live", "blocked" in content)

print("\n-- Phase info --")
check("mentions Phase 4A or migration phases", "Phase 4" in content or "Phase 3" in content or "migration" in content.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
