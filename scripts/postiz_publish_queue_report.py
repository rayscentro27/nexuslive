#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import showroom_assets as SA  # noqa: E402

OUT_MD = ROOT / "reports" / "showroom" / "postiz_publish_queue_report.md"
OUT_JSON = ROOT / "logs" / "postiz_publish_queue_latest.json"


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    queued = SA.by_status("ready_to_publish_pending_approval")
    payload = {
        "generated_at": now,
        "queued_assets": queued,
        "count": len(queued),
        "safe_mode": True,
        "publish_blocked": True,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    lines = [
        "# Postiz Publish Queue Report",
        f"_Generated: {now}_",
        "",
        f"- queued assets: {len(queued)}",
        "- publish blocked: yes",
        "- approval required: exact Ray approval for the exact post before any scheduling",
        "",
    ]
    if queued:
        lines.append("## Ready to Publish Pending Approval")
        for asset in queued:
            lines.append(
                f"- `{asset['asset_id']}` [{asset['asset_type']}] — {asset['title']} · {asset['showroom_path']}"
            )
    else:
        lines.append("No queued Postiz draft candidates right now.")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(OUT_MD.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
