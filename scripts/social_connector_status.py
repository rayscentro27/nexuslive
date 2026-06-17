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


def _fmt(platform: dict, *extra_fields: str) -> str:
    bits = [
        f"status={platform['status']}",
        f"account_connected={platform.get('account_connected')}",
        f"publishing_ready={platform.get('publishing_ready')}",
        f"source={platform.get('connection_source')}",
    ]
    for f in extra_fields:
        bits.append(f"{f}={platform.get(f)}")
    bits.append(f"token_present={platform.get('token_present')}")
    blk = ', '.join(platform.get('blockers') or []) or 'none'
    bits.append(f"blocker={blk}")
    return ' · '.join(str(b) for b in bits)


def write_reports(status: dict) -> dict[str, str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "social_connector_status_latest.json"
    md_path = REPORT_DIR / "social_connector_status_latest.md"
    json_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fb, ig, pz = status["facebook"], status["instagram"], status["postiz"]
    lines = [
        "# Social Connector Status - Latest",
        "",
        f"- Facebook: {_fmt(fb, 'page_id_present')}",
        f"  - page_id_alias={fb.get('page_id_alias')} · token_alias={fb.get('token_alias')} · permission_check_done={fb.get('permission_check_done')}",
        f"- Instagram: {_fmt(ig, 'instagram_account_id_present')}",
        f"  - account_id_alias={ig.get('instagram_account_id_alias')} · token_alias={ig.get('token_alias')} · media_flow_implemented={ig.get('media_flow_implemented')} · permission_check_done={ig.get('permission_check_done')}",
        f"- Postiz: {pz['status']} · account_connected={pz.get('account_connected')} · url_present={pz.get('url_present')} · api_key_present={pz.get('api_key_present')} · blocker={', '.join(pz.get('blockers') or []) or 'none'}",
        "",
        f"- Real publish enabled: {status['real_publish_enabled']}",
        f"- Dry-run mode: {status['dry_run']}",
        f"- Approval required: {status['approval_required']}",
        f"- Network check run: {status.get('network_checked')}",
        "",
        "Connection source is the repo-root .env (META_PAGE_ID / META_PAGE_ACCESS_TOKEN / "
        "META_INSTAGRAM_ACCOUNT_ID) — the same names content_employee/publisher.py uses.",
        "No secrets printed. No mutating API calls are ever made by this script.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path.relative_to(ROOT)), "markdown": str(md_path.relative_to(ROOT))}


def main() -> int:
    ap = argparse.ArgumentParser(description="Check social connector readiness without printing secrets.")
    ap.add_argument("--check-network", action="store_true", help="run a read-only Graph API identity GET (no mutations, no publishing)")
    args = ap.parse_args()
    status = connector_status(check_network=bool(args.check_network))
    status["network_check_requested"] = bool(args.check_network)
    status["network_checked"] = bool(args.check_network)
    status["report_paths"] = write_reports(status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
