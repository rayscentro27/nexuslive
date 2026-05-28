"""
run_youtube_intelligence_cycle.py
===================================
Run intelligence extraction for YouTube sources in the registry.

Usage:
  python scripts/run_youtube_intelligence_cycle.py --all
  python scripts/run_youtube_intelligence_cycle.py --source-id yt_abc12345
  python scripts/run_youtube_intelligence_cycle.py --status submitted
  python scripts/run_youtube_intelligence_cycle.py --url https://youtube.com/@channel

Produces per source:
  docs/reports/youtube/content_intelligence_<id>_<ts>.json
  docs/reports/youtube/monetization_intelligence_<id>_<ts>.json
  docs/reports/youtube/nexus_improvement_<id>_<ts>.json
  docs/reports/youtube/compliance_intelligence_<id>_<ts>.json
  docs/reports/youtube/youtube_intelligence_report_<id>_<ts>.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Intelligence Cycle")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--all",       action="store_true", help="Process all sources needing research")
    grp.add_argument("--source-id", type=str,            help="Process a specific source_id")
    grp.add_argument("--url",       type=str,            help="Process source by URL")
    grp.add_argument("--status",    type=str,            help="Process all sources with given status")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without extracting")
    args = parser.parse_args()

    from lib.youtube_source_registry import YouTubeSourceRegistry
    from lib.youtube_intelligence_extractor import YouTubeIntelligenceExtractor

    registry  = YouTubeSourceRegistry()
    extractor = YouTubeIntelligenceExtractor()

    # Build work list
    sources = []
    if args.all:
        sources = registry.needs_research()
        print(f"[{_now()}] Processing all {len(sources)} sources needing research...")
    elif args.source_id:
        src = registry.get(args.source_id)
        if not src:
            print(f"ERROR: source_id '{args.source_id}' not found in registry.")
            sys.exit(1)
        sources = [src]
    elif args.url:
        src = registry.find_by_url(args.url)
        if not src:
            print(f"ERROR: URL not found in registry. Register it first with run_youtube_source_reconciliation.py")
            sys.exit(1)
        sources = [src]
    elif args.status:
        sources = registry.by_status(args.status)  # type: ignore[arg-type]
        print(f"[{_now()}] Processing {len(sources)} sources with status='{args.status}'...")

    if not sources:
        print("No sources to process.")
        return

    if args.dry_run:
        print(f"[DRY RUN] Would process {len(sources)} sources:")
        for s in sources:
            d = s.to_dict()
            print(f"  {s.source_id[:8]} | {d['source_type']} | {d.get('channel_name') or d['url'][:50]}")
        return

    processed = 0
    failed    = 0
    compliance_flags = []

    for src in sources:
        d   = src.to_dict()
        sid = d["source_id"]
        url = d["url"]
        print(f"\n  [{processed+1}/{len(sources)}] Extracting: {sid[:8]} — {url[:60]}")

        try:
            bundle = extractor.extract(
                source_id=sid,
                url=url,
                channel_name=d.get("channel_name", ""),
                video_title=d.get("video_title", ""),
            )
            processed += 1
            print(f"    Artifacts saved: {len(bundle.artifact_paths)}")
            print(f"    Report: {bundle.report_path}")

            if bundle.has_compliance_flags():
                flags = bundle.compliance.get("risk_flags", [])
                compliance_flags.append({
                    "source_id":   sid,
                    "url":         url,
                    "risk_flags":  flags,
                })
                print(f"    ⚠ COMPLIANCE FLAGS: {flags}")
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

    print(f"\n[DONE] Intelligence extraction complete.")
    print(f"  Processed:  {processed}")
    print(f"  Failed:     {failed}")
    if compliance_flags:
        print(f"\n  ⚠ COMPLIANCE FLAGS FOUND ({len(compliance_flags)} sources):")
        for cf in compliance_flags:
            print(f"    {cf['source_id'][:8]} — {cf['url'][:50]}")
            for flag in cf["risk_flags"][:3]:
                print(f"      • {flag}")
        print("\n  These sources require compliance review before use in Nexus education.")


if __name__ == "__main__":
    main()
