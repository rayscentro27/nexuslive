#!/usr/bin/env python3
"""
run_content_pipeline.py — CLI entry point for the Nexus Content Pipeline.

Usage:
    python scripts/run_content_pipeline.py \\
        --topic "Why most businesses get denied funding and how AI can help fix readiness gaps" \\
        --platforms youtube newsletter

    python scripts/run_content_pipeline.py \\
        --topic "..." \\
        --platforms youtube \\
        --json-out /tmp/pipeline_result.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load project .env if present
_env = ROOT / ".env"
if _env.exists():
    with open(_env) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            import os
            _k, _, _v = _line.partition("=")
            _k = _k.strip()
            _v = _v.strip().strip('"').strip("'")
            if _k not in os.environ:
                os.environ[_k] = _v


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nexus Content Pipeline — multi-agent content assembly line"
    )
    parser.add_argument(
        "--topic", required=True,
        help="Content topic / research question"
    )
    parser.add_argument(
        "--platforms", nargs="+", default=["youtube", "newsletter"],
        choices=["youtube", "newsletter", "seo_article", "linkedin", "twitter"],
        help="Target platforms (default: youtube newsletter)"
    )
    parser.add_argument(
        "--json-out", default="",
        help="Optional: save full result JSON to this path"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-agent progress output"
    )
    args = parser.parse_args()

    if args.quiet:
        import os
        os.environ["NEXUS_PIPELINE_QUIET"] = "1"

    from lib.content_pipeline import ContentPipeline

    pipeline = ContentPipeline()
    try:
        result = pipeline.run(
            topic     = args.topic,
            platforms = args.platforms,
        )
    except RuntimeError as exc:
        print(f"\n[FATAL] {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, default=str))
        print(f"[pipeline] Full result saved → {out_path}")

    # Exit 0 if at least one platform reached approval_ready
    any_ready = any(
        pr.get("packet", {}).get("status") == "approval_ready"
        for pr in result.get("per_platform", {}).values()
    )
    sys.exit(0 if any_ready else 2)


if __name__ == "__main__":
    main()
