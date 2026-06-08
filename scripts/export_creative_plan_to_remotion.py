#!/usr/bin/env python3
"""
export_creative_plan_to_remotion.py — Nexus creative plan -> Remotion data JSON.

Reads a *.scenes.json (create_creative_short_plan.py) + the voiceover timing json
(generate_short_voiceover.py) and emits tool-lab/remotion-shorts/src/data/<id>.json
with per-scene durationInFrames synced to the narration. No posting, no network.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tool-lab" / "remotion-shorts" / "src" / "data"
FPS = 30


def main():
    ap = argparse.ArgumentParser(description="Export Nexus plan -> Remotion data json")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--timing", default=None, help="voiceover timing json (for per-scene durations)")
    ap.add_argument("--audio", default="voiceover.wav", help="audio file in remotion public/")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    plan = json.loads(Path(args.scenes).read_text())
    timing = {}
    tpath = args.timing
    if not tpath:
        stem = Path(args.scenes).name.replace(".scenes.json", "")
        cand = ROOT / "reports" / "tool_lab" / "creative_renders" / f"{stem}_voiceover_timing.json"
        tpath = str(cand) if cand.exists() else None
    if tpath and Path(tpath).exists():
        timing = {t["id"]: t["duration"] for t in json.loads(Path(tpath).read_text()).get("scenes", [])}

    scenes_out, frame_cursor = [], 0
    for s in plan["scenes"]:
        dur_s = timing.get(s["id"], 4.0)
        frames = max(int(round(dur_s * FPS)), 30)
        scenes_out.append({
            "id": s["id"], "label": s.get("label"), "onscreen": s.get("onscreen"),
            "caption": s.get("caption"), "vo": s.get("vo"), "visual": s.get("visual"),
            "motion": s.get("motion", "zoom_in"), "bg": s.get("bg", "navy"),
            "accent": s.get("accent", "blue"),
            "from": frame_cursor, "durationInFrames": frames,
        })
        frame_cursor += frames

    data = {
        "content_id": plan.get("content_id"),
        "title": plan.get("title"),
        "fps": FPS, "width": 1080, "height": 1920,
        "totalFrames": frame_cursor,
        "audio": args.audio,
        "disclosure": plan.get("disclosure"),
        "brand": "Nexus · GoClearOnline",
        "youtube": plan.get("youtube", {}),
        "scenes": scenes_out,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    cid = (plan.get("content_id") or "short").split("-")[0]
    out = Path(args.out) if args.out else DATA / f"{cid}.json"
    out.write_text(json.dumps(data, indent=2))
    print(f"wrote: {out}")
    print(f"scenes: {len(scenes_out)} · totalFrames: {frame_cursor} (~{frame_cursor/FPS:.1f}s @ {FPS}fps) · audio: {args.audio}")


if __name__ == "__main__":
    main()
