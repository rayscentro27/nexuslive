#!/usr/bin/env python3
"""
Nexus Review Queue CLI — Review proposed knowledge, strategy DNA, and opportunity intelligence.

Usage:
    python scripts/nexus_review_queue.py list-proposed
    python scripts/nexus_review_queue.py list-by-domain --domain grants
    python scripts/nexus_review_queue.py show-summary
    python scripts/nexus_review_queue.py approve --id <id> --by ray [--apply]
    python scripts/nexus_review_queue.py reject  --id <id> --by ray [--apply]
    python scripts/nexus_review_queue.py archive --id <id> --by ray [--apply]
    python scripts/nexus_review_queue.py export-review-report

Safety: dry-run by default. Use --apply to commit changes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.knowledge_review_queue import (
    list_records,
    update_status,
    VALID_STATUS,
)


DOMAINS = ["trading", "grants", "funding", "credit", "business_opportunities",
           "marketing", "operations", "automation", "system"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_row(r: dict, verbose: bool = False) -> None:
    rid = str(r.get("id") or "")[:18]
    domain = str(r.get("domain") or r.get("category") or "?")[:20]
    status = str(r.get("status") or "?")[:12]
    title = str(r.get("title") or r.get("topic") or "Untitled")[:60]
    score = r.get("quality_score")
    score_str = f"  q={score}" if score is not None else ""
    dry = "  [DRY]" if r.get("dry_run") else ""
    print(f"  {rid}  {domain:<20} {status:<12} {title}{score_str}{dry}")
    if verbose:
        content = str(r.get("content") or r.get("summary") or "")[:200]
        if content:
            print(f"           content: {content}")
        review = r.get("review") or {}
        if isinstance(review, dict) and review.get("notes"):
            print(f"           notes: {review['notes']}")


def cmd_list_proposed(args: argparse.Namespace) -> None:
    rows = list_records("proposed")
    if not rows:
        print("No proposed records found.")
        return
    print(f"\n{'ID':<18}  {'Domain':<20} {'Status':<12} Title")
    print("-" * 80)
    for r in rows:
        _print_row(r, verbose=getattr(args, "verbose", False))
    print(f"\nTotal: {len(rows)} proposed record(s)")


def cmd_list_by_domain(args: argparse.Namespace) -> None:
    domain = (args.domain or "").lower()
    all_rows = list_records()
    rows = [r for r in all_rows if str(r.get("domain") or r.get("category") or "").lower() == domain]
    if not rows:
        print(f"No records for domain '{domain}'.")
        return
    print(f"\nRecords for domain: {domain}")
    print(f"{'ID':<18}  {'Status':<12} Title")
    print("-" * 72)
    for r in rows:
        _print_row(r)
    print(f"\nTotal: {len(rows)}")


def cmd_show_summary(args: argparse.Namespace) -> None:
    all_rows = list_records()
    by_status: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    for r in all_rows:
        s = str(r.get("status") or "unknown")
        d = str(r.get("domain") or r.get("category") or "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        by_domain[d] = by_domain.get(d, 0) + 1

    print(f"\nNexus Review Queue Summary — {_now()}")
    print("=" * 50)
    print(f"\n  Total records: {len(all_rows)}")
    print("\n  By status:")
    for s, n in sorted(by_status.items()):
        print(f"    {s:<15} {n}")
    print("\n  By domain:")
    for d, n in sorted(by_domain.items()):
        print(f"    {d:<25} {n}")

    proposed = [r for r in all_rows if r.get("status") == "proposed"]
    high_quality = [r for r in proposed if (r.get("quality_score") or 0) >= 70]
    print(f"\n  Proposed: {len(proposed)}")
    print(f"  High quality (score≥70): {len(high_quality)}")

    if proposed:
        print("\n  Pending review (first 5):")
        for r in proposed[:5]:
            _print_row(r)


def cmd_approve(args: argparse.Namespace) -> None:
    _change_status(args, "approved")


def cmd_reject(args: argparse.Namespace) -> None:
    _change_status(args, "rejected")


def cmd_archive(args: argparse.Namespace) -> None:
    _change_status(args, "archived" if "archived" in VALID_STATUS else "rejected")


def _change_status(args: argparse.Namespace, new_status: str) -> None:
    record_id = args.id
    reviewed_by = getattr(args, "by", "ray") or "ray"
    notes = getattr(args, "notes", "") or ""
    apply_mode = getattr(args, "apply", False)

    if not record_id:
        print("Error: --id required")
        sys.exit(1)

    # Find the record first
    rows = list_records()
    match = next((r for r in rows if str(r.get("id") or "").startswith(record_id)), None)
    if not match:
        print(f"Record not found: {record_id}")
        sys.exit(1)

    print(f"\n{'[DRY RUN] ' if not apply_mode else ''}Changing status:")
    print(f"  ID:       {match.get('id')}")
    print(f"  Title:    {str(match.get('title') or '')[:60]}")
    print(f"  Domain:   {match.get('domain') or match.get('category')}")
    print(f"  From:     {match.get('status')} → {new_status}")
    print(f"  By:       {reviewed_by}")
    if notes:
        print(f"  Notes:    {notes}")

    if not apply_mode:
        print("\n[DRY RUN] No changes applied. Use --apply to commit.")
        return

    result = update_status(str(match["id"]), new_status, reviewed_by, notes)
    if result:
        print(f"\n✅ Status updated to '{new_status}'")
    else:
        print("\n❌ Update failed — record not found or invalid status.")


def cmd_export_review_report(args: argparse.Namespace) -> None:
    all_rows = list_records()
    report_path = ROOT / "reports" / "knowledge_intake" / f"review_report_{_now().replace(':', '-')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": _now(),
        "total": len(all_rows),
        "records": all_rows,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"✅ Review report exported: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nexus Review Queue — review proposed knowledge, strategies, opportunities"
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list-proposed", help="List all proposed records")
    p_list.add_argument("--verbose", "-v", action="store_true")

    p_domain = sub.add_parser("list-by-domain", help="List records by domain")
    p_domain.add_argument("--domain", required=True, choices=DOMAINS + ["?"],
                          help=f"Domain to filter: {', '.join(DOMAINS)}")

    sub.add_parser("show-summary", help="Summary of queue state")

    for cmd_name in ("approve", "reject", "archive"):
        p_cmd = sub.add_parser(cmd_name, help=f"{cmd_name.capitalize()} a record by ID")
        p_cmd.add_argument("--id", required=True, help="Record ID (prefix OK)")
        p_cmd.add_argument("--by", default="ray", help="Reviewer name (default: ray)")
        p_cmd.add_argument("--notes", default="", help="Review notes")
        p_cmd.add_argument("--apply", action="store_true", help="Commit the change (dry-run by default)")

    sub.add_parser("export-review-report", help="Export full review report to JSON")

    args = parser.parse_args()

    dispatch = {
        "list-proposed":     cmd_list_proposed,
        "list-by-domain":    cmd_list_by_domain,
        "show-summary":      cmd_show_summary,
        "approve":           cmd_approve,
        "reject":            cmd_reject,
        "archive":           cmd_archive,
        "export-review-report": cmd_export_review_report,
    }

    if not args.command:
        parser.print_help()
        sys.exit(0)

    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
