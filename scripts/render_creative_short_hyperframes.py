#!/usr/bin/env python3
"""
render_creative_short_hyperframes.py — render a HyperFrames composition to a DRAFT MP4.

Thin, safe wrapper around the local HyperFrames CLI (`npx hyperframes render`). It does
NOT post, upload, schedule, or touch credentials — it only turns an HTML composition
(produced by export_creative_plan_to_hyperframes.py) into a draft MP4 on disk.

Usage:
  python scripts/render_creative_short_hyperframes.py \
      --project tool-lab/hyperframes-shorts \
      --out reports/tool_lab/hyperframes_renders/<id>_hyperframes_v1.mp4 \
      [--quality draft|standard|high] [--fps 30]

On failure it does NOT fake success: it prints the CLI error and exits non-zero so the
caller can write a blocker report and keep the HTML composition as the artifact.

SAFETY: free/local only. No paid API. social_publish_executor.py remains the only
upload path; Ray approval remains required for publish/schedule/public actions.
"""
from __future__ import annotations
import argparse, subprocess, sys, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a HyperFrames composition to a draft MP4")
    ap.add_argument("--project", default=str(ROOT / "tool-lab" / "hyperframes-shorts"))
    ap.add_argument("--composition", default="index.html")
    ap.add_argument("--out", required=True, help="final MP4 path (draft only)")
    ap.add_argument("--quality", default="standard", choices=["draft", "standard", "high"])
    ap.add_argument("--fps", default="30")
    ap.add_argument("--workers", default="1", help="1 worker is safest on low-memory/macOS hosts")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    comp = project / args.composition
    if not comp.exists():
        print(f"ERROR: composition not found: {comp}", file=sys.stderr)
        print("Run export_creative_plan_to_hyperframes.py first.", file=sys.stderr)
        return 2

    # ABSOLUTE output path: the render runs with cwd=project, so a project-relative
    # -o would be resolved against project and double the path. Always pass absolute.
    local_out = project / "renders" / "hyperframes_draft.mp4"
    local_out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx", "--yes", "hyperframes@latest", "render",
        "-c", args.composition,
        "-o", str(local_out),
        "-q", args.quality,
        "-f", str(args.fps),
        "-w", str(args.workers),
        "--low-memory-mode",
    ]
    print("RUN:", " ".join(cmd), f"(cwd={project})")
    proc = subprocess.run(cmd, cwd=str(project))
    if proc.returncode != 0 or not local_out.exists():
        print(f"\nRENDER FAILED (exit {proc.returncode}). Not faking success.", file=sys.stderr)
        print("Keep the HTML composition as the artifact and write a blocker report.", file=sys.stderr)
        return proc.returncode or 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local_out, out)
    print(f"\nOK draft MP4: {out}")
    print("NOTE: draft only — not uploaded, not posted, not scheduled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
