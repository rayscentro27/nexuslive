#!/usr/bin/env python3
"""
run_monetization_decision_cycle.py
======================================
CLI entry point for the Hermes Monetization Decision Cycle.

Scores the latest intake sources and produces recommendations.
Can run standalone or as part of the daily intake cycle.

Usage:
  python3 scripts/run_monetization_decision_cycle.py --mode validation --top-n 10
  python3 scripts/run_monetization_decision_cycle.py --mode daily --top-n 20 --no-dry-run
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes Monetization Decision Cycle")
    parser.add_argument("--mode", default="validation",
        choices=["validation", "daily", "overnight"])
    parser.add_argument("--cost", default="free")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--no-dry-run", action="store_true")
    parser.add_argument("--intake-path", default="",
        help="Path to specific intake JSON (default: use latest registry)")
    args = parser.parse_args()

    dry_run = not args.no_dry_run

    print(f"=== Hermes Monetization Decision Cycle — mode={args.mode} top-n={args.top_n} "
          f"dry-run={dry_run} ===")
    print()

    # Load intake records
    intake_records: list[dict] = []
    if args.intake_path:
        import json
        p = Path(args.intake_path)
        if p.exists():
            data = json.loads(p.read_text())
            intake_records = data.get("records", [])
        else:
            print(f"Intake file not found: {args.intake_path}")
            return 1
    else:
        from lib.daily_opportunity_intake_engine import load_latest_intake
        intake_records = load_latest_intake(limit=100)
        if not intake_records:
            print("No intake records found. Run daily intake first:")
            print("  python3 scripts/run_daily_opportunity_intake.py --mode validation")
            return 1

    print(f"Loaded {len(intake_records)} intake records.")
    print()

    from lib.hermes_monetization_decision_engine import run_decision_cycle

    result = run_decision_cycle(
        intake_records=intake_records,
        mode=args.mode,
        top_n=args.top_n,
        dry_run=dry_run,
        cost=args.cost,
    )

    top_ops = result["top_opportunities"]
    rejected = result["rejected"]
    needs_approval = result["needs_approval"]

    print(f"Scored: {result['total_scored']}")
    print(f"Actionable: {len(top_ops)}")
    print(f"Rejected: {len(rejected)}")
    print(f"Needs approval: {len(needs_approval)}")
    print()

    if result.get("top_recommendation"):
        print(f"Best move: {result['top_recommendation']}")
        print()

    print("Top opportunities:")
    for i, op in enumerate(top_ops[:args.top_n], 1):
        flag = " ⏳" if op.get("requires_ray_approval") else ""
        print(f"  {i}. [{op['status']}] {op['title'][:70]}{flag} (score: {op['monetization_score']})")

    print()
    print(f"Decision report: {result['md_path']}")
    print(f"Top actions: {result['top_actions_path']}")
    print(f"Rejected log: {result['rejected_path']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
