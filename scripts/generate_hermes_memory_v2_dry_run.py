"""
generate_hermes_memory_v2_dry_run.py
Phase 3 / 3B — Hermes Memory v2 dry-run record generator.

Reads the Phase 3 audit/classification reports and produces proposed
hermes_memory_v2 records WITHOUT writing to Supabase.

Phase 3B: freshness rules from hermes_memory_freshness.py are applied to
annotate records for provider_health, executive_briefings, ai_task_queue,
nexus_skills, and agent_dispatch_tasks.

Usage:
  python scripts/generate_hermes_memory_v2_dry_run.py --write-report true
  python scripts/generate_hermes_memory_v2_dry_run.py --write-report true --phase3b true
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"
sys.path.insert(0, str(ROOT))

_SCOPE_MAP = {
    "active_live_answer": "live_answer",
    "historical_only":    "historical",
    "deprecated":         "historical",
    "blocked_from_live":  "blocked_from_telegram",
    "debug_only":         "debug_only",
    "needs_review":       "historical",
}

_STATUS_MAP = {
    "active_live_answer": "active",
    "historical_only":    "archived",
    "deprecated":         "deprecated",
    "blocked_from_live":  "blocked",
    "debug_only":         "active",
    "needs_review":       "needs_review",
}

# Do not write to Supabase — dry-run only
_SUPABASE_WRITE_ATTEMPTED = False

# Phase 3B: freshness windows (mirrors hermes_memory_freshness constants)
_PHASE3B_FRESHNESS_RULES: dict[str, dict] = {
    "provider_health": {
        "max_age_minutes": 15,
        "stale_values": ["OFFLINE", "offline", "Ollama OFFLINE", "Beehiiv pending",
                         "YouTube Studio pending", "OpenRouter not configured"],
        "stale_classification": "blocked_from_live",
        "description": "Records >15min old or with OFFLINE values must not reach Telegram",
    },
    "executive_briefings": {
        "max_age_hours": 48,
        "stale_classification": "historical_only",
        "description": "Briefings older than 48h are historical_only — not live answers",
    },
    "hermes_conversation_context": {
        "max_age_hours": 24,
        "stale_classification": "historical_only",
        "description": "Context >24h must not drive follow-up resolution",
    },
    "ai_task_queue": {
        "max_age_hours": 24,
        "active_statuses": ["queued", "running", "assigned", "pending", "in_progress"],
        "completed_statuses": ["completed", "done", "succeeded", "cancelled", "failed", "error"],
        "description": "Active status + fresh (<24h) → active; completed or stale → historical",
    },
    "agent_dispatch_tasks": {
        "max_age_hours": 24,
        "active_statuses": ["active", "pending", "running", "assigned", "in_progress"],
        "completed_statuses": ["completed", "done", "succeeded", "cancelled", "failed", "error"],
        "description": "Active status + fresh (<24h) → active; completed or stale → historical",
    },
    "nexus_skills": {
        "active_statuses": ["enabled", "active", "installed"],
        "inactive_statuses": ["disabled", "deprecated", "removed"],
        "description": "enabled/active/installed → active; disabled/deprecated → historical",
    },
}

# Tables affected by Phase 3B freshness rules
_PHASE3B_TABLES = frozenset(_PHASE3B_FRESHNESS_RULES.keys())

try:
    from lib.hermes_memory_freshness import classify_record as _freshness_classify_record
    _FRESHNESS_MODULE_AVAILABLE = True
except Exception:
    _FRESHNESS_MODULE_AVAILABLE = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_source_map() -> dict:
    candidates = sorted(MEMORY_DIR.glob("hermes_memory_source_map_*.json"), reverse=True)
    if not candidates:
        return {}
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def _load_supabase_classification() -> dict:
    candidates = sorted(MEMORY_DIR.glob("supabase_table_memory_classification_*.json"), reverse=True)
    if not candidates:
        return {}
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def _load_local_classification() -> dict:
    candidates = sorted(MEMORY_DIR.glob("local_memory_classification_*.json"), reverse=True)
    if not candidates:
        return {}
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def _load_fallback_audit() -> dict:
    candidates = sorted(MEMORY_DIR.glob("fallback_response_pattern_audit_*.json"), reverse=True)
    if not candidates:
        return {}
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def _make_record(
    source_id: str,
    title: str,
    summary: str,
    memory_type: str,
    classification: str,
    source: str,
    source_table: str = "",
    source_path: str = "",
    risk: str = "low",
    tags: list[str] | None = None,
    deprecated_reason: str = "",
    evidence_path: str = "",
    phase3b_rule: dict | None = None,
) -> dict:
    status = _STATUS_MAP.get(classification, "needs_review")
    scope = _SCOPE_MAP.get(classification, "historical")
    migration_note = "Phase 3 dry-run. No Supabase writes. Proposed status: {}.".format(status)
    if phase3b_rule:
        migration_note += " Phase 3B freshness rule applied: {}.".format(
            phase3b_rule.get("description", "freshness check"))
    return {
        "memory_id":             f"mv2-{source_id.lower()}-{uuid.uuid4().hex[:8]}",
        "title":                 title,
        "summary":               summary,
        "memory_type":           memory_type,
        "status":                status,
        "scope":                 scope,
        "source":                source,
        "source_table":          source_table,
        "source_path":           source_path,
        "source_record_id":      "",
        "evidence_path":         evidence_path or "docs/reports/memory/hermes_memory_source_map_*.json",
        "related_action_id":     "",
        "related_decision_id":   "",
        "related_goal_id":       "",
        "related_source_id":     source_id,
        "related_artifact_id":   "",
        "related_scout":         "",
        "confidence":            0.9 if status == "active" else 0.7,
        "priority":              "high" if risk == "critical" else "medium" if risk == "high" else "low",
        "tags":                  tags or [classification, risk],
        "payload":               {"classification": classification, "risk": risk,
                                  "phase3b_freshness_rule": phase3b_rule or {}},
        "migration_status":      "dry_run",
        "migration_notes":       migration_note,
        "deprecated_reason":     deprecated_reason,
        "replacement_memory_id": "",
        "created_at":            _now_iso(),
    }


def generate_records() -> list[dict]:
    records: list[dict] = []

    source_map = _load_source_map()
    supabase_class = _load_supabase_classification()
    local_class = _load_local_classification()
    fallback_audit = _load_fallback_audit()

    # ── Supabase tables ──────────────────────────────────────────────────────
    for tbl in (supabase_class.get("tables") or source_map.get("supabase_tables", [])):
        sid = tbl.get("source_id", "?")
        table = tbl.get("table", "?")
        cls = tbl.get("classification", "needs_review")
        risk = tbl.get("risk", "low")
        # Phase 3B: attach freshness rule metadata for affected tables
        phase3b_rule = _PHASE3B_FRESHNESS_RULES.get(table)
        records.append(_make_record(
            source_id=sid,
            title=f"Supabase: {table}",
            summary=f"Supabase table {table!r} — classified as {cls}",
            memory_type="supabase_table",
            classification=cls,
            source="supabase",
            source_table=table,
            risk=risk,
            tags=["supabase", cls, risk] + (["phase3b_freshness"] if phase3b_rule else []),
            evidence_path="docs/reports/memory/supabase_table_memory_classification_*.json",
            phase3b_rule=phase3b_rule,
        ))

    # ── Local files ──────────────────────────────────────────────────────────
    for lf in (local_class.get("files") or source_map.get("local_files", [])):
        sid = lf.get("source_id", "?")
        path = lf.get("path", "?")
        cls = lf.get("classification", "needs_review")
        risk = lf.get("risk", "low")
        records.append(_make_record(
            source_id=sid,
            title=f"Local: {Path(path).name if '*' not in path else path}",
            summary=f"Local file {path!r} — classified as {cls}",
            memory_type="local_json" if path.endswith(".json") else "artifact_folder" if path.endswith("/") else "jsonl" if ".jsonl" in path else "artifact_folder",
            classification=cls,
            source="local_filesystem",
            source_path=path,
            risk=risk,
            tags=["local", cls, risk],
            evidence_path="docs/reports/memory/local_memory_classification_*.json",
        ))

    # ── Code fallbacks ───────────────────────────────────────────────────────
    for cf in (fallback_audit.get("patterns") or source_map.get("code_fallbacks", [])):
        sid = cf.get("source_id", "?")
        loc = cf.get("location", "?")
        desc = cf.get("description", "")
        cls = cf.get("classification", "needs_review")
        risk = cf.get("risk", "low")
        deprecated_reason = "Replaced by hermes_monetization_today.py" if cls == "deprecated" else ""
        records.append(_make_record(
            source_id=sid,
            title=f"Fallback: {sid}",
            summary=f"{desc} — classified as {cls}",
            memory_type="code_fallback",
            classification=cls,
            source=loc,
            risk=risk,
            deprecated_reason=deprecated_reason,
            tags=["code_fallback", cls, risk],
            evidence_path="docs/reports/memory/fallback_response_pattern_audit_*.json",
        ))

    return records


def write_reports(records: list[dict], ts: str) -> tuple[Path, Path]:
    jsonl_path = MEMORY_DIR / f"hermes_memory_v2_dry_run_{ts}.jsonl"
    md_path    = MEMORY_DIR / f"hermes_memory_v2_dry_run_{ts}.md"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    counts: dict[str, int] = {}
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# hermes_memory_v2 Dry-Run Records\n")
        f.write(f"*Generated: {_now_iso()} — {len(records)} records*\n\n")
        f.write(f"**No Supabase writes. Dry-run only.**\n\n")
        f.write("## Status Summary\n\n")
        for status, count in sorted(counts.items()):
            f.write(f"- {status}: {count}\n")
        f.write("\n## Records\n\n")
        for r in records:
            f.write(f"### {r['memory_id']}\n")
            f.write(f"- **Title:** {r['title']}\n")
            f.write(f"- **Status:** {r['status']}\n")
            f.write(f"- **Scope:** {r['scope']}\n")
            f.write(f"- **Memory type:** {r['memory_type']}\n")
            f.write(f"- **Source:** {r['source']}\n")
            if r["source_table"]:
                f.write(f"- **Table:** {r['source_table']}\n")
            if r["source_path"]:
                f.write(f"- **Path:** {r['source_path']}\n")
            if r["deprecated_reason"]:
                f.write(f"- **Deprecated reason:** {r['deprecated_reason']}\n")
            f.write(f"- **Migration notes:** {r['migration_notes']}\n\n")

    return jsonl_path, md_path


def write_phase3b_reports(records: list[dict], ts: str) -> tuple[Path, Path]:
    """Generate Phase 3B stale safety refinement reports."""
    phase3b_records = [r for r in records if r.get("payload", {}).get("phase3b_freshness_rule")]
    affected_tables = list(_PHASE3B_TABLES)

    json_path = MEMORY_DIR / f"phase3b_stale_safety_refinement_{ts}.json"
    md_path   = MEMORY_DIR / f"phase3b_stale_safety_refinement_{ts}.md"

    report = {
        "phase": "3B",
        "generated_at": _now_iso(),
        "description": "Stale-record safety rules applied to Phase 3 dry-run classification",
        "supabase_write_attempted": False,
        "freshness_module_available": _FRESHNESS_MODULE_AVAILABLE,
        "affected_tables": affected_tables,
        "rules": _PHASE3B_FRESHNESS_RULES,
        "annotated_records_count": len(phase3b_records),
        "total_records_count": len(records),
        "annotated_records": [
            {
                "memory_id": r["memory_id"],
                "title": r["title"],
                "status": r["status"],
                "source_table": r["source_table"],
                "freshness_rule": r["payload"]["phase3b_freshness_rule"],
            }
            for r in phase3b_records
        ],
    }
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Phase 3B — Stale Safety Refinement Report\n\n")
        f.write(f"*Generated: {_now_iso()}*\n\n")
        f.write("**No Supabase writes. Classification and annotation only.**\n\n")
        f.write(f"Freshness module loaded: {'YES' if _FRESHNESS_MODULE_AVAILABLE else 'NO (rules embedded)'}\n\n")
        f.write("## Freshness Rules Applied\n\n")
        for table, rule in _PHASE3B_FRESHNESS_RULES.items():
            f.write(f"### {table}\n")
            f.write(f"{rule.get('description', '')}\n\n")
            if "max_age_minutes" in rule:
                f.write(f"- Max age: {rule['max_age_minutes']} minutes\n")
            if "max_age_hours" in rule:
                f.write(f"- Max age: {rule['max_age_hours']} hours\n")
            if "stale_values" in rule:
                f.write(f"- Stale values: {', '.join(rule['stale_values'])}\n")
            if "active_statuses" in rule:
                f.write(f"- Active statuses: {', '.join(rule['active_statuses'])}\n")
            f.write(f"- Stale classification: {rule.get('stale_classification', 'historical_only')}\n\n")
        f.write(f"## Annotated Records ({len(phase3b_records)} of {len(records)})\n\n")
        for r in phase3b_records:
            f.write(f"- **[{r['status']}]** {r['title']} ({r['source_table']})\n")

    return json_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", default="false")
    parser.add_argument("--phase3b", default="false")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    records = generate_records()
    print(f"Generated {len(records)} proposed hermes_memory_v2 records (dry-run)")

    do_write = args.write_report.lower() in ("true", "1", "yes")
    do_phase3b = args.phase3b.lower() in ("true", "1", "yes")

    if do_write:
        jsonl_path, md_path = write_reports(records, ts)
        print(f"Written: {jsonl_path.relative_to(ROOT)}")
        print(f"Written: {md_path.relative_to(ROOT)}")
    else:
        for r in records[:5]:
            print(f"  [{r['status']}] {r['title']}")
        if len(records) > 5:
            print(f"  ... and {len(records) - 5} more")

    if do_phase3b or do_write:
        json_path, md_path2 = write_phase3b_reports(records, ts)
        print(f"Written: {json_path.relative_to(ROOT)}")
        print(f"Written: {md_path2.relative_to(ROOT)}")
        phase3b_count = sum(1 for r in records if r.get("payload", {}).get("phase3b_freshness_rule"))
        print(f"Phase 3B: {phase3b_count} records annotated with freshness rules")
        print(f"Phase 3B: affected tables: {', '.join(sorted(_PHASE3B_TABLES))}")

    print("Supabase write attempted: NO")
    print("Data changed: NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
