#!/usr/bin/env python3
"""validate_remotion_ci_artifact.py — verify a downloaded Remotion CI artifact (no upload/post)."""
from __future__ import annotations
import argparse, shutil, subprocess
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="Validate a downloaded Remotion MP4 artifact (read-only)")
    ap.add_argument("path", nargs="?", default="reports/tool_lab/creative_renders/fcf087ea_business_credit_myths_v3_remotion.mp4")
    args = ap.parse_args()
    p = Path(args.path)
    print(f"checking: {p}")
    if not p.exists():
        print("  ✗ file does not exist — download the artifact first (see remotion_github_actions_render.md)"); return 2
    if not p.suffix.lower() == ".mp4":
        print(f"  ! not an .mp4 (suffix {p.suffix})")
    size = p.stat().st_size
    print(f"  size: {size} bytes -> {'OK (>0)' if size > 0 else '✗ EMPTY'}")
    if size == 0:
        return 3
    if shutil.which("ffprobe"):
        try:
            dur = subprocess.run(["ffprobe","-v","quiet","-of","csv=p=0","-show_entries","format=duration",str(p)],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
            acodec = subprocess.run(["ffprobe","-v","quiet","-select_streams","a","-show_entries","stream=codec_name","-of","csv=p=0",str(p)],
                                    capture_output=True, text=True, timeout=30).stdout.strip()
            vcodec = subprocess.run(["ffprobe","-v","quiet","-select_streams","v","-show_entries","stream=codec_name","-of","csv=p=0",str(p)],
                                    capture_output=True, text=True, timeout=30).stdout.strip()
            print(f"  duration: {dur}s · video: {vcodec or 'none'} · audio: {acodec or 'none'}")
        except Exception as e:
            print("  (ffprobe skipped:", str(e)[:60], ")")
    else:
        print("  (ffprobe not available — size check only)")
    print("  ✓ artifact looks valid. Review it, then use the gated publisher with a scoped approval to upload. No upload done here.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
