"""
generate_hermes_memory_v2_dry_run.py
Phase 3 — Hermes Memory v2 dry-run record generator.

Reads the Phase 3 audit/classification reports and produces proposed
hermes_memory_v2 records WITHOUT writing to Supabase.

Usage:
  python scripts/generate_hermes_memory_v2_dry_run.py --write-report true
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
) -> dict:
    status = _STATUS_MAP.get(classification, "needs_review")
    scope = _SCOPE_MAP.get(classification, "historical")
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
        "evidence_path":         evidence_path or f"docs/reports/memory/hermes_memory_source_map_*.json",
        "related_action_id":     "",
        "related_decision_id":   "",
        "related_goal_id":       "",
        "related_source_id":     source_id,
        "related_artifact_id":   "",
        "related_scout":         "",
        "confidence":            0.9 if status == "active" else 0.7,
        "priority":              "high" if risk == "critical" else "medium" if risk == "high" else "low",
        "tags":                  tags or [classification, risk],
        "payload":               {"classification": classification, "risk": risk},
        "migration_status":      "dry_run",
        "migration_notes":       f"Phase 3 dry-run. No Supabase writes. Proposed status: {status}.",
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
        records.append(_make_record(
            source_id=sid,
            title=f"Supabase: {table}",
            summary=f"Supabase table {table!r} — classified as {cls}",
            memory_type="supabase_table",
            classification=cls,
            source="supabase",
            source_table=table,
            risk=risk,
            tags=["supabase", cls, risk],
            evidence_path="docs/reports/memory/supabase_table_memory_classification_*.json",
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", default="false")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    records = generate_records()
    print(f"Generated {len(records)} proposed hermes_memory_v2 records (dry-run)")

    if args.write_report.lower() in ("true", "1", "yes"):
        jsonl_path, md_path = write_reports(records, ts)
        print(f"Written: {jsonl_path.relative_to(ROOT)}")
        print(f"Written: {md_path.relative_to(ROOT)}")
    else:
        for r in records[:5]:
            print(f"  [{r['status']}] {r['title']}")
        if len(records) > 5:
            print(f"  ... and {len(records) - 5} more")

    print("Supabase write attempted: NO")
    print("Data changed: NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
