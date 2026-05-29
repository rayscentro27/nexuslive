"""
run_hermes_operating_loop.py
=============================
CLI entry point for the Hermes Operating Loop.

Usage:
  python scripts/run_hermes_operating_loop.py --mode validation --max-actions 5
  python scripts/run_hermes_operating_loop.py --mode daily
  python scripts/run_hermes_operating_loop.py --mode digest-only
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

parser = argparse.ArgumentParser(description="Hermes Operating Loop")
parser.add_argument("--mode", default="validation",
                    choices=["validation", "daily", "continue", "digest-only"],
                    help="Loop mode")
parser.add_argument("--max-actions", type=int, default=5,
                    help="Max actions to create or propose")
parser.add_argument("--no-dry-run", action="store_true",
                    help="Actually create actions (default is dry-run for safety)")
args = parser.parse_args()

dry_run = not args.no_dry_run

print(f"\n=== Hermes Operating Loop — mode={args.mode} max-actions={args.max_actions} dry-run={dry_run} ===\n")

# Initialize registries first
try:
    from lib.hermes_goal_registry import initialize_registry as init_goals
    init_goals()
    print("✅ Goal registry initialized")
except Exception as exc:
    print(f"  ⚠️  Goal registry init failed: {exc}")

try:
    from lib.hermes_tool_scout_registry import initialize_registry as init_scouts
    init_scouts()
    print("✅ Tool/scout registry initialized")
except Exception as exc:
    print(f"  ⚠️  Scout registry init failed: {exc}")

# Run the loop
from lib.hermes_operating_loop import run_operating_loop
result = run_operating_loop(
    mode=args.mode,
    max_actions=args.max_actions,
    dry_run=dry_run,
)

print("\n" + "─" * 60)
print(result.digest)
print("─" * 60)
print(f"\nArtifact: {result.artifact_path}")
print(f"Decisions logged: {len(result.decisions_logged)}")
print(f"Actions created: {len(result.actions_created)}")
print()
sys.exit(0)
