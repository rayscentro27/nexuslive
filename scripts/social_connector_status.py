#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.social_publishers import connector_status  # noqa: E402


REPORT_DIR = ROOT / "reports" / "social"


def write_reports(status: dict) -> dict[str, str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "social_connector_status_latest.json"
    md_path = REPORT_DIR / "social_connector_status_latest.md"
    json_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Social Connector Status - Latest",
        "",
        f"- Postiz: {status['postiz']['status']} ({', '.join(status['postiz']['blockers']) or 'ready'})",
        f"- Facebook: {status['facebook']['status']} ({', '.join(status['facebook']['blockers']) or 'ready'})",
        f"- Instagram: {status['instagram']['status']} ({', '.join(status['instagram']['blockers']) or 'ready'})",
        f"- Real publish enabled: {status['real_publish_enabled']}",
        f"- Dry-run mode: {status['dry_run']}",
        f"- Approval required: {status['approval_required']}",
        "",
        "No secrets printed. No network check was run unless explicitly requested.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path.relative_to(ROOT)), "markdown": str(md_path.relative_to(ROOT))}


def main() -> int:
    ap = argparse.ArgumentParser(description="Check social connector readiness without printing secrets.")
    ap.add_argument("--check-network", action="store_true", help="reserved; no API calls are made in this safe implementation")
    args = ap.parse_args()
    status = connector_status()
    status["network_check_requested"] = bool(args.check_network)
    status["network_checked"] = False
    status["report_paths"] = write_reports(status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
