#!/usr/bin/env python3
"""
run_weekly_github_trend_research.py — CLI for Nexus GitHub Trend Research

Usage:
    python scripts/run_weekly_github_trend_research.py
    python scripts/run_weekly_github_trend_research.py --json-out /tmp/trends.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.exists():
    import os
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip(); v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v


def main() -> None:
    parser = argparse.ArgumentParser(description="Nexus Weekly GitHub Trend Researcher")
    parser.add_argument("--json-out", default="", help="Optional: save result JSON")
    args = parser.parse_args()

    from lib.github_trend_researcher import GitHubTrendResearcher

    print("\n[trends] Starting GitHub trend research…")
    researcher = GitHubTrendResearcher()
    result     = researcher.run()

    source = result.get("source_status", "unknown")
    count  = result.get("repos_fetched", 0)
    print(f"[trends] Source: {source} | Repos evaluated: {count}")

    if result.get("unavailability_reason"):
        print(f"[trends] ⚠️  Web unavailable: {result['unavailability_reason']}")

    print("\n[trends] Top 3 worth testing:")
    for r in result.get("top_3_worth_testing", []):
        print(f"  - {r}")

    rec = result.get("top_1_recommendation", {})
    if rec:
        print(f"\n[trends] #1 Recommendation: {rec.get('name', 'N/A')}")
        print(f"  Improves: {rec.get('nexus_process_improved', '')}")

    print(f"\n[trends] Artifacts:")
    for k, v in result.get("artifacts", {}).items():
        status = "✅" if v and Path(v).exists() else "❌"
        print(f"  {status} {k}: {Path(v).name if v else 'MISSING'}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, default=str))
        print(f"\n[trends] Full result → {out}")

    sys.exit(0 if result.get("artifacts") else 1)


if __name__ == "__main__":
    main()
