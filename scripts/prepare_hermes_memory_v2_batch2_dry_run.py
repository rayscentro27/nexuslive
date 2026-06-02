"""
prepare_hermes_memory_v2_batch2_dry_run.py
Phase 4D — Batch 2 dry-run preparation.

Selects and validates proposed Batch 2 records for hermes_memory_v2.
Batch 2 allowed types: lesson, goal, tool_registry, scout_registry

DRY-RUN ONLY — no Supabase writes, no INSERT.
Output reports to docs/reports/memory/.

To apply Batch 2 (after Ray approval), run:
  python scripts/backfill_hermes_memory_v2.py --apply ...
  with confirmation: I APPROVE HERMES MEMORY V2 BACKFILL BATCH 2
"""
import argparse, json, os, sys, re
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

_SUPABASE_WRITE_ATTEMPTED = False  # sentinel — must remain False at all times

BATCH2_ALLOWED_TYPES = {"lesson", "goal", "tool_registry", "scout_registry"}

BATCH2_EXCLUDED_TYPES = {
    "provider_status_snapshot", "executive_briefings", "ai_task_queue",
    "agent_dispatch_tasks", "fallback_rule", "debug_note", "archived_note",
    "template",
}

STALE_MARKERS = [
    "Ollama OFFLINE", "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "Executive Memory — as of",
    "Quality escalation fallback", "NitroTrades fabricated status",
    "fake pending approvals",
]

REQUIRED_FIELDS = [
    "memory_id", "title", "summary", "memory_type", "status", "scope",
    "confidence", "priority", "tags", "payload", "migration_status",
    "created_at", "updated_at",
]

ALLOWED_STATUSES = {"active"}
ALLOWED_SCOPES = {"live_answer"}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_stale(record: dict) -> str | None:
    text = f"{record.get('title', '')} {record.get('summary', '')}"
    for m in STALE_MARKERS:
        if m.lower() in text.lower():
            return m
    return None


def _validate(record: dict) -> list[str]:
    errors = []
    missing = [f for f in REQUIRED_FIELDS if f not in record or record[f] is None]
    if missing:
        errors.append(f"missing fields: {missing}")
    mt = record.get("memory_type", "")
    if mt not in BATCH2_ALLOWED_TYPES:
        errors.append(f"type {mt!r} not in Batch 2 allowed types {sorted(BATCH2_ALLOWED_TYPES)}")
    if mt in BATCH2_EXCLUDED_TYPES:
        errors.append(f"type {mt!r} is explicitly excluded from Batch 2")
    if record.get("status") not in ALLOWED_STATUSES:
        errors.append(f"status {record.get('status')!r} not allowed (must be 'active')")
    if record.get("scope") not in ALLOWED_SCOPES:
        errors.append(f"scope {record.get('scope')!r} not allowed (must be 'live_answer')")
    stale = _has_stale(record)
    if stale:
        errors.append(f"stale marker: {stale!r}")
    if not isinstance(record.get("priority"), int):
        errors.append(f"priority must be int, got {type(record.get('priority')).__name__}")
    return errors


def _batch2_candidates() -> list[dict]:
    """Hand-crafted Batch 2 candidate records.

    Types: lesson, goal, tool_registry, scout_registry
    All: status=active, scope=live_answer
    No stale markers, no secrets, no provider snapshots.
    """
    now = _now()
    return [
        # ── lesson records ─────────────────────────────────────────────────────
        {
            "memory_id":        "mv2-lesson-01-a1b2c3d4",
            "title":            "Memory Safety Contract: never fall back to stale defaults",
            "summary":          "Hermes must return empty/neutral on memory unavailability rather than impersonating live state with archived defaults.",
            "memory_type":      "lesson",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.97,
            "priority":         95,
            "tags":             ["memory", "safety", "compliance"],
            "payload":          {"source": "phase3_safety_refinement", "applies_to": "all_telegram_paths"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        {
            "memory_id":        "mv2-lesson-02-b2c3d4e5",
            "title":            "Evidence-first principle: never mark a task complete without evidence_ref",
            "summary":          "Completing tasks without evidence led to phantom progress. All completions must cite an artifact, commit hash, or Supabase record as evidence.",
            "memory_type":      "lesson",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.95,
            "priority":         90,
            "tags":             ["evidence", "tasks", "compliance"],
            "payload":          {"source": "operational_philosophy", "applies_to": "task_completion"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        {
            "memory_id":        "mv2-lesson-03-c3d4e5f6",
            "title":            "Telegram dedup: _contains_forbidden_content 'sources:' blocked memory responses",
            "summary":          "The pattern 'sources:' in _FORBIDDEN_CONTENT_PATTERNS was too broad — it matched 'Live answer sources:' in memory command responses, causing silent send failures. Fixed by removing the pattern.",
            "memory_type":      "lesson",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.98,
            "priority":         85,
            "tags":             ["telegram", "debugging", "memory_commands"],
            "payload":          {"source": "phase4d_repair", "commit": "a43b48b"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        # ── goal records ───────────────────────────────────────────────────────
        {
            "memory_id":        "mv2-goal-01-d4e5f6a7",
            "title":            "Achieve $1,000/week autonomous revenue through Nexus intelligence",
            "summary":          "Primary financial goal: build autonomous revenue streams via Nexus platform reaching $1K/week. Requires launch of invite-only beta, content flywheel, and proven intelligence workers.",
            "memory_type":      "goal",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.90,
            "priority":         95,
            "tags":             ["revenue", "mission", "autonomous"],
            "payload":          {"target_weekly_usd": 1000, "timeline": "2026"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        {
            "memory_id":        "mv2-goal-02-e5f6a7b8",
            "title":            "Launch Nexus invite-only beta with funding intelligence",
            "summary":          "Launch Nexus platform as an invite-only beta focused on funding intelligence, credit strategy, and business credit access for small business owners.",
            "memory_type":      "goal",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.88,
            "priority":         90,
            "tags":             ["launch", "beta", "funding_intelligence"],
            "payload":          {"phase": "pre-launch", "audience": "small_business_funding"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        {
            "memory_id":        "mv2-goal-03-f6a7b8c9",
            "title":            "Complete hermes_memory_v2 migration with full live reader switch",
            "summary":          "Migrate all relevant memory to hermes_memory_v2 in controlled batches, complete reader comparison, and switch live Telegram reader after Ray approval.",
            "memory_type":      "goal",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.92,
            "priority":         88,
            "tags":             ["memory_v2", "migration", "hermes"],
            "payload":          {"current_phase": "4D", "next_phase": "4E"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        # ── tool_registry records ──────────────────────────────────────────────
        {
            "memory_id":        "mv2-tool-01-a7b8c9d0",
            "title":            "Hermes Gateway v0.11.0 — Nexus central orchestration",
            "summary":          "Hermes is the central intelligence layer for Nexus. Routes Telegram commands, enforces memory safety, coordinates workers, and enforces NEXUS_DRY_RUN globally.",
            "memory_type":      "tool_registry",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.98,
            "priority":         90,
            "tags":             ["hermes", "gateway", "orchestration"],
            "payload":          {"version": "0.11.0", "primary_interface": "telegram"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        {
            "memory_id":        "mv2-tool-02-b8c9d0e1",
            "title":            "Supabase — primary data persistence layer for Nexus",
            "summary":          "Supabase (PostgreSQL) is the primary database for Nexus. Hosts hermes_memory_v2, hermes_executive_memory, action_queue, hermes_aggregates, and other operational tables.",
            "memory_type":      "tool_registry",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.97,
            "priority":         88,
            "tags":             ["supabase", "database", "persistence"],
            "payload":          {"tables": ["hermes_memory_v2", "hermes_executive_memory", "action_queue"]},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        {
            "memory_id":        "mv2-tool-03-c9d0e1f2",
            "title":            "hermes_memory_v2 — structured memory table with safety guardrails",
            "summary":          "27-column Supabase table for structured Hermes memory. Enforces CHECK constraints on memory_type, status, scope, and confidence. Replaces unstructured executive memory with versioned, typed records.",
            "memory_type":      "tool_registry",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.96,
            "priority":         87,
            "tags":             ["memory_v2", "supabase", "structured_memory"],
            "payload":          {"phase": "4D", "batch1_rows": 15, "reader_status": "preview"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        # ── scout_registry records ─────────────────────────────────────────────
        {
            "memory_id":        "mv2-scout-01-d0e1f2a3",
            "title":            "Content Scout — monitors YouTube and blog content for funding intelligence",
            "summary":          "Content Scout worker monitors funding-related YouTube channels and blogs. Ingests summaries into Supabase source_intake. Runs in dry-run mode; does not publish without approval.",
            "memory_type":      "scout_registry",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.88,
            "priority":         80,
            "tags":             ["scout", "content", "youtube", "intelligence"],
            "payload":          {"mode": "dry_run", "intake_table": "source_intake"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
        {
            "memory_id":        "mv2-scout-02-e1f2a3b4",
            "title":            "Research Scout — web research worker for opportunity intelligence",
            "summary":          "Research Scout performs structured web research on funding opportunities, grant programs, and business credit. Outputs to Supabase. All research is advisory; no autonomous spend.",
            "memory_type":      "scout_registry",
            "status":           "active",
            "scope":            "live_answer",
            "confidence":       0.87,
            "priority":         78,
            "tags":             ["scout", "research", "opportunity"],
            "payload":          {"mode": "dry_run", "output": "research_artifacts"},
            "migration_status": "pending",
            "created_at":       now,
            "updated_at":       now,
        },
    ]


def _check_existing_jsonl_for_batch2_types(jsonl_paths: list[Path]) -> dict:
    """Scan existing dry-run JSONLs for any Batch 2 type records."""
    found = []
    for path in jsonl_paths:
        try:
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                    if r.get("memory_type") in BATCH2_ALLOWED_TYPES:
                        found.append({"source": path.name, "record": r.get("memory_id"), "type": r.get("memory_type")})
                except Exception:
                    pass
        except Exception:
            pass
    return {"found": found, "count": len(found)}


def main() -> int:
    assert _SUPABASE_WRITE_ATTEMPTED is False, "Write sentinel violated"

    parser = argparse.ArgumentParser(description="Phase 4D — Batch 2 dry-run preparation")
    parser.add_argument("--limit", type=int, default=25, help="Max records to select (default: 25)")
    parser.add_argument("--output-dir", default=str(MEMORY_DIR))
    args = parser.parse_args()

    assert _SUPABASE_WRITE_ATTEMPTED is False
    ts = _ts()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Phase 4D — Batch 2 Dry-Run Preparation ===")
    print()
    print(f"Mode         : DRY-RUN ONLY — no Supabase writes")
    print(f"Allowed types: {sorted(BATCH2_ALLOWED_TYPES)}")
    print(f"Max records  : {args.limit}")
    print()

    # Scan existing JSONLs for any Batch 2 types
    existing_jsonls = sorted(MEMORY_DIR.glob("hermes_memory_v2_dry_run_*.jsonl"))
    existing_scan = _check_existing_jsonl_for_batch2_types(existing_jsonls)
    if existing_scan["count"] > 0:
        print(f"Found {existing_scan['count']} Batch 2-type records in existing JSONLs:")
        for item in existing_scan["found"]:
            print(f"  {item['source']}: {item['record']} ({item['type']})")
    else:
        print("No Batch 2-type records found in existing dry-run JSONLs.")
        print("Using hand-crafted candidate records for dry-run.")
    print()

    # Load candidates
    candidates = _batch2_candidates()

    # Filter and validate
    selected = []
    excluded = []
    needs_ray_review = []

    for r in candidates:
        errors = _validate(r)
        if errors:
            excluded.append({"id": r.get("memory_id", "?"), "type": r.get("memory_type", "?"),
                              "title": r.get("title", "?")[:50], "reasons": errors})
        else:
            selected.append(r)
            # Flag any records that should require Ray review before apply
            if r.get("confidence", 1.0) < 0.85:
                needs_ray_review.append(r.get("memory_id"))

    selected = selected[:args.limit]

    # Type breakdown
    type_counts = Counter(r.get("memory_type") for r in selected)

    # Stale string check
    stale_detected = [r.get("memory_id") for r in selected if _has_stale(r)]

    print(f"Candidates   : {len(candidates)}")
    print(f"Selected     : {len(selected)}")
    print(f"Excluded     : {len(excluded)}")
    print(f"Needs review : {len(needs_ray_review)}")
    print(f"Stale strings: {len(stale_detected)}")
    print()
    print("Type breakdown:")
    for mt, cnt in sorted(type_counts.items()):
        print(f"  {mt}: {cnt}")
    print()

    print(f"Selected records ({len(selected)}):")
    for r in selected:
        print(f"  {r['memory_id']:38s} | {r['memory_type']:15s} | {r['title'][:55]}")

    if excluded:
        print(f"\nExcluded ({len(excluded)}):")
        for e in excluded:
            print(f"  {e['id']:38s} | {e['type']:15s} | {e['reasons']}")

    if stale_detected:
        print(f"\nWARNING: stale strings found in: {stale_detected}")
    else:
        print("\nStale string check: PASS — no stale markers found")

    # Schema validation pass
    schema_errors = sum(1 for r in selected if _validate(r))
    print(f"Schema validation: {'PASS' if schema_errors == 0 else f'FAIL ({schema_errors} errors)'}")

    print()
    print("=" * 60)
    print("NO SUPABASE WRITES PERFORMED.")
    print("This is a dry-run only.")
    print()
    print("To apply Batch 2, Ray must approve with exact text:")
    print("  I APPROVE HERMES MEMORY V2 BACKFILL BATCH 2")
    print("=" * 60)
    print()

    assert _SUPABASE_WRITE_ATTEMPTED is False, "Write sentinel — must be False"

    # Write dry-run JSONL
    jsonl_path = output_dir / f"phase4d_batch2_dry_run_{ts}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in selected:
            f.write(json.dumps(r, default=str) + "\n")

    # Write JSON report
    report = {
        "phase":                "4D",
        "batch":                "batch2",
        "generated_at":         _now(),
        "mode":                 "dry_run",
        "source":               "hand_crafted_candidates",
        "existing_jsonl_scan":  existing_scan,
        "candidates_count":     len(candidates),
        "selected_count":       len(selected),
        "excluded_count":       len(excluded),
        "allowed_types":        sorted(BATCH2_ALLOWED_TYPES),
        "excluded_types":       sorted(BATCH2_EXCLUDED_TYPES),
        "type_breakdown":       dict(type_counts),
        "stale_detected":       stale_detected,
        "needs_ray_review":     needs_ray_review,
        "schema_errors":        schema_errors,
        "supabase_writes_attempted": False,
        "batch2_applied":       False,
        "live_reader_switched": False,
        "selected_ids":         [r["memory_id"] for r in selected],
        "excluded_detail":      excluded,
        "approval_required_text": "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 2",
    }
    json_path = output_dir / f"phase4d_batch2_dry_run_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # Write Markdown report
    md_lines = [
        "# Phase 4D — Batch 2 Dry-Run Report",
        "",
        f"*Generated: {report['generated_at']}*",
        "",
        "**No Supabase writes. Dry-run only.**",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Phase | 4D |",
        f"| Mode | DRY-RUN ONLY |",
        f"| Candidates | {len(candidates)} |",
        f"| Selected | {len(selected)} |",
        f"| Excluded | {len(excluded)} |",
        f"| Allowed types | {', '.join(sorted(BATCH2_ALLOWED_TYPES))} |",
        f"| Stale strings detected | {len(stale_detected)} |",
        f"| Schema errors | {schema_errors} |",
        f"| Supabase writes | NO |",
        f"| Batch 2 applied | NO |",
        f"| Live reader switched | NO |",
        "",
        "## Type Breakdown",
        "",
    ]
    for mt, cnt in sorted(type_counts.items()):
        md_lines.append(f"- **{mt}**: {cnt}")
    md_lines += [
        "",
        "## Selected Records",
        "",
    ]
    for r in selected:
        md_lines.append(f"- `{r['memory_id']}` — **{r['memory_type']}** — {r['title']}")
    if excluded:
        md_lines += ["", "## Excluded Records", ""]
        for e in excluded:
            md_lines.append(f"- `{e['id']}` ({e['type']}): {e['reasons']}")
    md_lines += [
        "",
        "## To Apply Batch 2",
        "",
        "Ray must approve with exact phrase:",
        "",
        "```",
        "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 2",
        "```",
        "",
        "Then run:",
        "```bash",
        "python scripts/backfill_hermes_memory_v2.py --apply --batch-name batch2 "
        "--require-ray-approval --confirm-text 'I APPROVE HERMES MEMORY V2 BACKFILL BATCH 2'",
        "```",
    ]
    md_path = output_dir / f"phase4d_batch2_dry_run_{ts}.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Reports written:")
    print(f"  {jsonl_path.name}")
    print(f"  {json_path.name}")
    print(f"  {md_path.name}")

    assert _SUPABASE_WRITE_ATTEMPTED is False
    return 0


if __name__ == "__main__":
    sys.exit(main())
