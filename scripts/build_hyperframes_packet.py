#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import showroom_assets as SA  # noqa: E402

PACKET_DIR = ROOT / "outputs" / "content" / "video_packets"
STORYBOARD_DIR = ROOT / "outputs" / "content" / "storyboards"
THUMB_DIR = ROOT / "outputs" / "content" / "thumbnail_prompts"


def latest(glob: str) -> Path | None:
    matches = sorted(ROOT.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def parse_short(path: Path) -> dict:
    text = path.read_text(errors="ignore")
    title = re.search(r"# YouTube Short Draft — (.+)", text)
    hook = re.search(r"## Hook\n(.+?)\n\n## Script", text, re.S)
    script = re.search(r"## Script \(≤60s\)\n(.+?)\n\n## Caption", text, re.S)
    return {
        "title": title.group(1).strip() if title else path.stem,
        "hook": (hook.group(1).strip() if hook else "").splitlines()[0] if hook else "",
        "voiceover": script.group(1).strip() if script else text[:500],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    short = latest("reports/content_engine/generated/youtube_shorts/*.md")
    plan = latest("reports/content_engine/generated/hyperframes_plans/*.md")
    avatar = latest("reports/content_engine/generated/avatar_video_packets/*.md")
    if not short:
        print("No YouTube short script found.")
        return 1

    meta = parse_short(short)
    asset_key = short.stem.replace("_youtube_short", "")
    packet = {
        "asset_id": f"hyperframes_{asset_key}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script_path": str(short.relative_to(ROOT)),
        "hyperframes_plan_path": str(plan.relative_to(ROOT)) if plan else None,
        "avatar_packet_path": str(avatar.relative_to(ROOT)) if avatar else None,
        "title": meta["title"],
        "hook": meta["hook"],
        "voiceover": meta["voiceover"],
        "scene_list": [
            "Hook statement",
            "Core explanation",
            "Pattern interrupt / proof",
            "CTA close",
        ],
        "visual_prompts": [
            "Bold 9:16 motion-graphics opener with high-contrast headline",
            "Clean explainer panels with kinetic captions and branded accent bar",
            "Myth vs truth contrast frames with simple icons",
            "Closing CTA card with disclosure-safe footer",
        ],
        "thumbnail_prompt": f"Vertical short thumbnail for '{meta['title']}' with a bold 3-5 word hook, high contrast, business credibility theme, no profit claims.",
        "status": "needs_review",
        "review_command": "python3 scripts/review_showroom_asset.py --asset-id <asset_id> --status approved_with_notes --feedback \"...\"",
        "feedback_command": "python3 scripts/review_showroom_asset.py --asset-id <asset_id> --status revise --feedback \"...\"",
        "approval_command": "python3 scripts/review_showroom_asset.py --asset-id <asset_id> --status ready_to_publish_pending_approval --feedback \"Approved exact post for scheduling only.\"",
    }

    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    STORYBOARD_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    packet_json = PACKET_DIR / f"{asset_key}_hyperframes_packet.json"
    packet_md = PACKET_DIR / f"{asset_key}_hyperframes_packet.md"
    storyboard_md = STORYBOARD_DIR / f"{asset_key}_storyboard.md"
    thumb_md = THUMB_DIR / f"{asset_key}_thumbnail_prompt.md"

    if not args.dry_run:
        packet_json.write_text(json.dumps(packet, indent=2))
        packet_md.write_text(
            "# HyperFrames Packet\n\n"
            f"- asset_id: `{packet['asset_id']}`\n"
            f"- title: {packet['title']}\n"
            f"- script path: `{packet['script_path']}`\n"
            f"- hyperframes plan path: `{packet['hyperframes_plan_path'] or 'none'}`\n"
            f"- avatar packet path: `{packet['avatar_packet_path'] or 'none'}`\n"
            f"- hook: {packet['hook']}\n"
            f"- status: {packet['status']}\n"
        )
        storyboard_md.write_text(
            "# Storyboard\n\n" + "\n".join(f"- Scene {i + 1}: {scene}" for i, scene in enumerate(packet["scene_list"])) + "\n"
        )
        thumb_md.write_text("# Thumbnail Prompt\n\n" + packet["thumbnail_prompt"] + "\n")
        SA.register(
            "video_packet",
            f"{packet['title']} HyperFrames Packet",
            str(packet_md.relative_to(ROOT)),
            showroom_path=str(packet_md.relative_to(ROOT)),
            key=packet["asset_id"],
        )

    print(packet_md.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
