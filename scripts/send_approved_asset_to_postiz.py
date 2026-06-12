#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import showroom_assets as SA  # noqa: E402

OUT_JSON = ROOT / "logs" / "postiz_draft_payload_latest.json"
OUT_MD = ROOT / "reports" / "showroom" / "postiz_draft_payload_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-id", required=False)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    assets = SA.recent(100)
    candidate = None
    if args.asset_id:
        candidate = next((a for a in assets if a["asset_id"] == args.asset_id), None)
    else:
        candidate = next((a for a in assets if a.get("status") == "ready_to_publish_pending_approval"), None)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": True,
        "postiz_connected": False,
        "scheduled": False,
        "candidate": candidate,
        "result": "no_candidate" if not candidate else "draft_only_payload_prepared",
        "approval_required": True,
        "auto_post_blocked": True,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    lines = [
        "# Postiz Draft Payload",
        f"_Generated: {payload['generated_at']}_",
        "",
        f"- dry run: yes",
        f"- candidate found: {'yes' if candidate else 'no'}",
        "- postiz connected: no",
        "- scheduled: no",
        "- auto-post blocked: yes",
    ]
    if candidate:
        lines += [
            "",
            "## Candidate",
            f"- asset_id: `{candidate['asset_id']}`",
            f"- title: {candidate['title']}",
            f"- type: {candidate['asset_type']}",
            f"- showroom path: {candidate['showroom_path']}",
            "- next step: after Ray approves the exact post, wire a draft-only Postiz adapter",
        ]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(OUT_MD.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
