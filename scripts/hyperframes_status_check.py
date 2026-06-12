#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_MD = ROOT / "reports" / "showroom" / "hyperframes_status.md"
OUT_JSON = ROOT / "logs" / "hyperframes_status_latest.json"


def newest(glob: str) -> Path | None:
    matches = sorted(ROOT.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    latest_plan = newest("reports/content_engine/generated/hyperframes_plans/*.md")
    latest_packet = newest("reports/content_engine/generated/avatar_video_packets/*.md")
    latest_render = newest("reports/tool_lab/hyperframes_renders/*_hyperframes_v1.mp4")
    latest_report = newest("reports/tool_lab/hyperframes_renders/*_hyperframes_render_report.md")
    payload = {
        "generated_at": now,
        "installed": (ROOT / "tool-lab" / "hyperframes").exists(),
        "packet_generation_active": bool(latest_plan or latest_packet),
        "local_free_mode": True,
        "paid_api_required": False,
        "latest_plan": str(latest_plan.relative_to(ROOT)) if latest_plan else None,
        "latest_packet": str(latest_packet.relative_to(ROOT)) if latest_packet else None,
        "latest_render": str(latest_render.relative_to(ROOT)) if latest_render else None,
        "latest_render_report": str(latest_report.relative_to(ROOT)) if latest_report else None,
        "showroom_connected": (ROOT / "outputs" / "content" / "scripts").exists(),
        "telegram_connected": False,
        "feedback_learning_connected": (ROOT / "logs" / "content_feedback_latest.json").exists(),
        "next_approval_needed": "Approve any external video generation/upload path separately. Current mode is local packet + draft render only.",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    lines = [
        "# HyperFrames Status",
        f"_Generated: {now}_",
        "",
        f"- installed: {'yes' if payload['installed'] else 'no'}",
        f"- packet generation active: {'yes' if payload['packet_generation_active'] else 'no'}",
        f"- local/free mode: {'yes' if payload['local_free_mode'] else 'no'}",
        f"- paid API required: {'yes' if payload['paid_api_required'] else 'no'}",
        f"- latest plan: {payload['latest_plan'] or 'none'}",
        f"- latest packet: {payload['latest_packet'] or 'none'}",
        f"- latest render: {payload['latest_render'] or 'none'}",
        f"- latest render report: {payload['latest_render_report'] or 'none'}",
        f"- showroom connected: {'yes' if payload['showroom_connected'] else 'no'}",
        f"- feedback learning connected: {'yes' if payload['feedback_learning_connected'] else 'no'}",
        "",
        "## Safe interpretation",
        "- HyperFrames is already usable locally as a packet/render layer.",
        "- Current lane is packet generation + local draft render only.",
        "- No upload or public posting path is active from this layer.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(OUT_MD.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
