#!/usr/bin/env python3
"""
run_daily_opportunity_intake.py
================================
CLI entry point for the Nexus Daily Opportunity Intake Engine.

Collects, registers, and organizes opportunity sources for Hermes.
Then scores them via monetization decision engine and produces a digest.

Usage:
  python3 scripts/run_daily_opportunity_intake.py --mode validation --cost free --max-sources 20
  python3 scripts/run_daily_opportunity_intake.py --mode daily --max-sources 50
  python3 scripts/run_daily_opportunity_intake.py --mode youtube-only --max-sources 10
  python3 scripts/run_daily_opportunity_intake.py --mode github-only --max-sources 10

Modes:
  validation        — dry-run, max 20 sources, no real actions created
  daily             — full run, max 50 sources
  overnight         — full run, max 100 sources
  keyword-only      — only keyword-based sources
  youtube-only      — only YouTube sources
  github-only       — only GitHub sources
  monetization-only — only monetization category sources

Defaults are safe (dry-run). Use --no-dry-run to create real action queue entries.
"""
import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nexus Daily Opportunity Intake Engine"
    )
    parser.add_argument("--mode", default="validation",
        choices=["validation", "daily", "overnight",
                 "keyword-only", "youtube-only", "github-only", "monetization-only"],
        help="Intake mode (default: validation)")
    parser.add_argument("--cost", default="free",
        choices=["free", "paid"],
        help="Cost constraint (default: free — no paid APIs)")
    parser.add_argument("--max-sources", type=int, default=None,
        help="Maximum sources to collect (default: 20 for validation, 50 for daily)")
    parser.add_argument("--register-artifacts", type=str, default="true",
        choices=["true", "false"])
    parser.add_argument("--no-dry-run", action="store_true",
        help="Actually create action queue entries (default: dry-run)")
    parser.add_argument("--skip-decision-cycle", action="store_true",
        help="Only run intake, skip monetization scoring")
    parser.add_argument("--top-n", type=int, default=10,
        help="Top N opportunities in decision cycle (default: 10)")
    args = parser.parse_args()

    dry_run = not args.no_dry_run
    register_artifacts = args.register_artifacts.lower() == "true"
    cost = args.cost

    # Default max sources by mode
    if args.max_sources is None:
        max_sources = {
            "validation": 20,
            "daily": 50,
            "overnight": 100,
            "keyword-only": 30,
            "youtube-only": 20,
            "github-only": 15,
            "monetization-only": 15,
        }.get(args.mode, 20)
    else:
        max_sources = args.max_sources

    if cost == "paid":
        print("⚠️  Paid APIs require Ray approval. Running with free-only sources.")
        cost = "free"

    print(f"=== Nexus Daily Opportunity Intake — mode={args.mode} max-sources={max_sources} "
          f"dry-run={dry_run} ===")
    print()

    # ── Phase 1: Intake ────────────────────────────────────────────────────────
    from lib.daily_opportunity_intake_engine import run_intake

    intake = run_intake(
        mode=args.mode,
        max_sources=max_sources,
        register_artifacts=register_artifacts,
        dry_run=dry_run,
        cost=cost,
    )

    stats = intake["stats"]
    print("Phase 1 — Sources collected:")
    print(f"  Total: {stats['total']}")
    print(f"  YouTube: {stats['youtube']}  Google: {stats['google']}  "
          f"GitHub: {stats['github']}  Social: {stats['social']}  "
          f"Monetization: {stats['monetization']}")
    print(f"  Real sources: {stats['real_sources']}  Fallback tasks: {stats['fallbacks']}")
    print(f"  Intake artifact: {intake['md_path']}")
    print()

    if args.skip_decision_cycle:
        print("Decision cycle skipped (--skip-decision-cycle).")
        return 0

    # ── Phase 2: Monetization decision cycle ──────────────────────────────────
    from lib.hermes_monetization_decision_engine import run_decision_cycle

    decision = run_decision_cycle(
        intake_records=intake["records"],
        mode=args.mode,
        top_n=args.top_n,
        dry_run=dry_run,
        cost=cost,
    )

    top_ops = decision["top_opportunities"]
    rejected = decision["rejected"]
    needs_approval = decision["needs_approval"]

    print("Phase 2 — Monetization decisions:")
    print(f"  Total scored: {decision['total_scored']}")
    print(f"  Actionable: {len(top_ops)}")
    print(f"  Rejected: {len(rejected)}")
    print(f"  Needs Ray approval: {len(needs_approval)}")
    if decision.get("top_recommendation"):
        print(f"  Best move: {decision['top_recommendation']}")
    print(f"  Decision report: {decision['md_path']}")
    print(f"  Top actions: {decision['top_actions_path']}")
    print()

    # ── Phase 3: Daily digest ─────────────────────────────────────────────────
    from lib.hermes_daily_monetization_digest import build_digest

    digest = build_digest(
        intake_results=intake,
        decision_results=decision,
    )

    print("Phase 3 — Daily digest prepared:")
    print(f"  Review artifact: {digest['review_md_path']}")
    print()

    # ── Separator + digest preview ────────────────────────────────────────────
    print("─" * 60)
    print("TELEGRAM DIGEST PREVIEW (would be sent to Ray):")
    print("─" * 60)
    print(digest["telegram_message"])
    print("─" * 60)
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("=== Summary ===")
    print(f"Sources: {stats['total']}  Actionable: {len(top_ops)}  "
          f"Rejected: {len(rejected)}  Approval needed: {len(needs_approval)}")
    print(f"Dry run: {dry_run}  Scheduler: NOT enabled")
    print()
    if top_ops:
        print("Top 3 opportunities:")
        for i, op in enumerate(top_ops[:3], 1):
            approval_flag = " ⏳" if op.get("requires_ray_approval") else ""
            print(f"  {i}. [{op['status']}] {op['title'][:70]}{approval_flag}")
    if needs_approval:
        print("Needs Ray approval:")
        for item in needs_approval[:3]:
            print(f"  ⏳ {item['title'][:60]} — {item.get('approval_reason','')[:50]}")
    print()
    print(f"Review: {digest['review_md_path']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
