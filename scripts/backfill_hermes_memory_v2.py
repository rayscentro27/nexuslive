"""
backfill_hermes_memory_v2.py
Backfill approved records into hermes_memory_v2 in controlled batches.
Default: dry-run. Apply requires --require-ray-approval + exact confirm text.
Never writes to old tables. Never prints secrets.
"""
import argparse, json, os, sys, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

_SUPABASE_WRITE_ATTEMPTED = False

BATCH_CONFIRM_TEXTS = {
    "batch1": "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 1",
    "batch2": "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 2",
    "batch3": "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 3",
}

BATCH_ALLOWED_TYPES = {
    "batch1": {"operating_rule", "ray_preference", "approval_policy", "project_context"},
    "batch2": {"lesson", "goal", "tool_registry", "scout_registry"},
}

ALLOWED_STATUSES_FOR_INSERT = {"active"}
ALLOWED_SCOPES_FOR_INSERT = {"live_answer"}

OLD_TABLES = {
    "ai_memory", "hermes_executive_memory", "hermes_response_patterns",
    "memory_links", "knowledge_items", "business_opportunities",
    "executive_briefings", "provider_health", "ai_task_queue",
    "agent_dispatch_tasks", "human_approval_requests", "nexus_skills",
}

STALE_MARKERS = [
    "Ollama OFFLINE", "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "Quality escalation fallback",
    "Executive Memory — as of",
]

REQUIRED_FIELDS = [
    "memory_id", "title", "summary", "memory_type", "status", "scope",
    "confidence", "priority", "tags", "payload", "migration_status",
    "created_at", "updated_at",
]

ALLOWED_MEMORY_TYPES = frozenset([
    "operating_rule", "ray_preference", "project_context", "goal",
    "tool_registry", "scout_registry", "approval_policy",
    "provider_status_snapshot", "source_intake", "action", "decision",
    "artifact", "lesson", "template", "fallback_rule", "archived_note",
    "debug_note",
])


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def _redact(s: str) -> str:
    return re.sub(r"eyJ[A-Za-z0-9_\-\.]+", "[REDACTED]", str(s))


def _check_env() -> list[str]:
    missing = []
    if not os.environ.get("SUPABASE_URL", "").strip():
        missing.append("SUPABASE_URL")
    if not os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip():
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    return missing


def _check_manifest() -> tuple[bool, str]:
    manifests = sorted(MEMORY_DIR.glob("backup_manifest_*.json"))
    if not manifests:
        return False, "No backup manifest found"
    m = json.loads(manifests[-1].read_text(encoding="utf-8"))
    if not m.get("ready_for_phase4b"):
        return False, f"Manifest not ready_for_phase4b: {manifests[-1].name}"
    generated_at = m.get("generated_at", "")
    if generated_at:
        try:
            dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - dt
            if age > timedelta(hours=48):
                return False, f"Manifest is {age.total_seconds()/3600:.1f}h old (max 48h for backfill)"
        except ValueError:
            pass
    return True, manifests[-1].name


def _has_stale_marker(record: dict) -> str | None:
    text = f"{record.get('title','')} {record.get('summary','')}"
    for m in STALE_MARKERS:
        if m.lower() in text.lower():
            return m
    return None


def _validate_record(record: dict, batch_types: set) -> list[str]:
    errors = []
    missing = [f for f in REQUIRED_FIELDS if f not in record or record[f] is None]
    if missing:
        errors.append(f"missing required fields: {missing}")
    mt = record.get("memory_type", "")
    if mt not in ALLOWED_MEMORY_TYPES:
        errors.append(f"invalid memory_type: {mt!r}")
    if mt not in batch_types:
        errors.append(f"memory_type {mt!r} not allowed in this batch")
    if record.get("status") not in ALLOWED_STATUSES_FOR_INSERT:
        errors.append(f"status {record.get('status')!r} not allowed for insert")
    if record.get("scope") not in ALLOWED_SCOPES_FOR_INSERT:
        errors.append(f"scope {record.get('scope')!r} not allowed for insert")
    stale = _has_stale_marker(record)
    if stale:
        errors.append(f"stale marker detected: {stale!r}")
    if not isinstance(record.get("priority"), int):
        errors.append(f"priority must be int, got {type(record.get('priority'))}")
    return errors


def load_and_filter(jsonl_path: Path, batch_name: str, limit: int, batch_types: set):
    records = [json.loads(l) for l in jsonl_path.read_text().splitlines() if l.strip()]
    selected = []
    excluded = []
    for r in records:
        errors = _validate_record(r, batch_types)
        if errors:
            excluded.append({"record": r.get("memory_id","?"), "reason": errors})
        else:
            selected.append(r)
    selected = selected[:limit]
    return selected, excluded, records


def run_dry_run(args) -> int:
    print(f"=== Backfill Dry-Run: {args.batch_name} ===\n")
    ts = _ts()

    # Load JSONL
    jsonl_path = Path(args.source_jsonl)
    if not jsonl_path.exists():
        print(f"ERROR: JSONL not found: {jsonl_path}")
        return 1

    batch_types = set(args.types.split(",")) if args.types else BATCH_ALLOWED_TYPES.get(args.batch_name, set())
    selected, excluded, all_records = load_and_filter(jsonl_path, args.batch_name, args.limit, batch_types)

    print(f"Source JSONL  : {jsonl_path}")
    print(f"Total records : {len(all_records)}")
    print(f"Eligible      : {len(selected)}")
    print(f"Excluded      : {len(excluded)}")
    print(f"Limit         : {args.limit}")
    print()

    print(f"Selected records ({len(selected)}):")
    for r in selected:
        print(f"  {r['memory_id']:35s} | {r['memory_type']:20s} | {r['title'][:55]}")

    if excluded:
        print(f"\nExcluded records ({len(excluded)}):")
        for e in excluded:
            print(f"  {e['record']:35s} | {e['reason']}")

    # Schema validation
    errors_found = 0
    for r in selected:
        errs = _validate_record(r, batch_types)
        if errs:
            errors_found += 1
            print(f"  SCHEMA ERROR {r.get('memory_id')}: {errs}")

    print(f"\nSchema validation: {'PASS' if errors_found == 0 else f'FAIL ({errors_found} errors)'}")

    # Write dry-run reports
    result = {
        "phase": "4C",
        "batch": args.batch_name,
        "generated_at": _now(),
        "mode": "dry_run",
        "source_jsonl": str(jsonl_path),
        "total_records": len(all_records),
        "eligible": len(selected),
        "excluded": len(excluded),
        "limit": args.limit,
        "selected_ids": [r["memory_id"] for r in selected],
        "excluded_detail": excluded,
        "schema_errors": errors_found,
        "writes_attempted": False,
    }
    md_path = MEMORY_DIR / f"phase4c_{args.batch_name}_backfill_dry_run_{ts}.md"
    json_path = MEMORY_DIR / f"phase4c_{args.batch_name}_backfill_dry_run_{ts}.json"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_make_dry_run_md(result, selected), encoding="utf-8")
    print(f"\nDry-run report: {json_path.name}")
    print(f"Dry-run report: {md_path.name}")
    print(f"\nNo writes. Ready to apply: {'YES' if errors_found == 0 and len(selected) > 0 else 'NO'}")
    return 0 if errors_found == 0 and len(selected) > 0 else 1


def _make_dry_run_md(result: dict, selected: list) -> str:
    lines = [
        f"# Phase 4C Batch 1 Backfill — Dry-Run Report",
        f"",
        f"*Generated: {result['generated_at']}*",
        f"",
        f"## Summary",
        f"",
        f"| Item | Value |",
        f"|---|---|",
        f"| Source JSONL | {result['source_jsonl']} |",
        f"| Total records | {result['total_records']} |",
        f"| Eligible | {result['eligible']} |",
        f"| Excluded | {result['excluded']} |",
        f"| Schema errors | {result['schema_errors']} |",
        f"| Writes attempted | {result['writes_attempted']} |",
        f"",
        f"## Selected Records",
        f"",
    ]
    for r in selected:
        lines.append(f"- `{r['memory_id']}` — **{r['memory_type']}** — {r['title']}")
    return "\n".join(lines) + "\n"


def run_apply(args) -> int:
    print(f"=== Backfill Apply: {args.batch_name} ===\n")
    ts = _ts()
    errors: list[str] = []

    # Guard 1: --require-ray-approval
    if not args.require_ray_approval:
        errors.append("--require-ray-approval flag missing")

    # Guard 2: exact confirm text
    required_text = BATCH_CONFIRM_TEXTS.get(args.batch_name, "")
    provided = (args.confirm_text or "").strip()
    if provided != required_text:
        errors.append(f"Confirm text mismatch. Required: {required_text!r} / Got: {provided!r}")

    # Guard 3: env vars
    missing_env = _check_env()
    if missing_env:
        errors.append(f"Env vars not set: {', '.join(missing_env)}")

    # Guard 4: manifest
    manifest_ok, manifest_msg = _check_manifest()
    if not manifest_ok:
        errors.append(f"Backup manifest: {manifest_msg}")

    # Guard 5: JSONL
    jsonl_path = Path(args.source_jsonl)
    if not jsonl_path.exists():
        errors.append(f"Source JSONL not found: {jsonl_path}")

    if errors:
        print("  APPLY BLOCKED:")
        for e in errors:
            print(f"  ✗ {e}")
        print("\n  Supabase writes: NO")
        return 1

    batch_types = set(args.types.split(",")) if args.types else BATCH_ALLOWED_TYPES.get(args.batch_name, set())
    selected, excluded, all_records = load_and_filter(jsonl_path, args.batch_name, args.limit, batch_types)

    if not selected:
        print("  No eligible records after filtering. Nothing to insert.")
        return 1

    print(f"  All guards passed. Connecting to Supabase...")
    try:
        client = _get_client()
    except Exception as exc:
        print(f"  ERROR: {_redact(str(exc))}")
        return 1

    # Verify table exists and is empty enough
    try:
        resp = client.table("hermes_memory_v2").select("memory_id", count="exact").execute()
        existing_count = resp.count if resp.count is not None else len(resp.data)
        existing_ids = {r["memory_id"] for r in resp.data}
        print(f"  hermes_memory_v2 current row count: {existing_count}")
    except Exception as exc:
        print(f"  ERROR checking table: {_redact(str(exc))}")
        return 1

    # Never write to old tables — final check
    for t in OLD_TABLES:
        if t in str(jsonl_path):
            print(f"  SAFETY ERROR: JSONL path references old table {t!r}. Aborting.")
            return 1

    inserted = []
    skipped_dup = []
    failed = []

    for r in selected:
        mid = r["memory_id"]
        if mid in existing_ids:
            skipped_dup.append(mid)
            print(f"  SKIP (duplicate) {mid}")
            continue
        # Prepare row — only include columns that exist in the schema
        row = {k: v for k, v in r.items() if k in [
            "memory_id", "title", "summary", "memory_type", "status", "scope",
            "confidence", "priority", "tags", "payload", "source", "source_table",
            "source_record_id", "migration_status", "created_at", "updated_at",
        ]}
        # Mark as applied
        row["migration_status"] = "applied"
        row["updated_at"] = _now()
        try:
            client.table("hermes_memory_v2").insert(row).execute()
            inserted.append(mid)
            print(f"  INSERT OK: {mid} | {r.get('memory_type')} | {r.get('title','')[:50]}")
        except Exception as exc:
            msg = _redact(str(exc))
            failed.append({"id": mid, "error": msg[:200]})
            print(f"  INSERT FAIL: {mid} — {msg[:120]}")

    print(f"\n  Inserted : {len(inserted)}")
    print(f"  Skipped  : {len(skipped_dup)} (duplicate)")
    print(f"  Failed   : {len(failed)}")
    print(f"  Excluded : {len(excluded)} (filtered out)")

    # Post-apply row count
    try:
        resp2 = client.table("hermes_memory_v2").select("memory_id", count="exact").execute()
        final_count = resp2.count if resp2.count is not None else len(resp2.data)
        print(f"\n  hermes_memory_v2 row count after apply: {final_count}")
    except Exception:
        final_count = None

    # Write apply reports
    result = {
        "phase": "4C",
        "batch": args.batch_name,
        "generated_at": _now(),
        "mode": "apply",
        "source_jsonl": str(jsonl_path),
        "selected_count": len(selected),
        "inserted": len(inserted),
        "inserted_ids": inserted,
        "skipped_duplicate": len(skipped_dup),
        "skipped_ids": skipped_dup,
        "failed": len(failed),
        "failed_detail": failed,
        "excluded": len(excluded),
        "hermes_memory_v2_row_count": final_count,
        "old_tables_modified": False,
        "secrets_printed": False,
        "writes_attempted": True,
        "writes_target": "hermes_memory_v2 only",
    }
    json_path = MEMORY_DIR / f"phase4c_{args.batch_name}_backfill_apply_{ts}.json"
    md_path = MEMORY_DIR / f"phase4c_{args.batch_name}_backfill_apply_{ts}.md"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_make_apply_md(result), encoding="utf-8")
    print(f"\n  Apply report: {json_path.name}")
    return 0 if len(failed) == 0 else 1


def _make_apply_md(result: dict) -> str:
    lines = [
        f"# Phase 4C {result['batch'].title()} Backfill — Apply Report",
        f"",
        f"*Generated: {result['generated_at']}*",
        f"",
        f"## Results",
        f"",
        f"| Item | Count |",
        f"|---|---|",
        f"| Inserted | {result['inserted']} |",
        f"| Skipped (duplicate) | {result['skipped_duplicate']} |",
        f"| Failed | {result['failed']} |",
        f"| Excluded (filtered) | {result['excluded']} |",
        f"| hermes_memory_v2 row count | {result['hermes_memory_v2_row_count']} |",
        f"",
        f"## Safety",
        f"",
        f"| Check | Result |",
        f"|---|---|",
        f"| Old tables modified | {result['old_tables_modified']} |",
        f"| Secrets printed | {result['secrets_printed']} |",
        f"| Writes target | {result['writes_target']} |",
    ]
    if result.get("inserted_ids"):
        lines += ["", "## Inserted IDs", ""]
        for mid in result["inserted_ids"]:
            lines.append(f"- `{mid}`")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Backfill hermes_memory_v2 in controlled batches")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-name", default="batch1")
    parser.add_argument("--types", default="")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--source-jsonl", required=True)
    parser.add_argument("--require-ray-approval", action="store_true")
    parser.add_argument("--confirm-text", default="")
    args = parser.parse_args()

    if args.apply:
        sys.exit(run_apply(args))
    else:
        sys.exit(run_dry_run(args))


if __name__ == "__main__":
    main()
