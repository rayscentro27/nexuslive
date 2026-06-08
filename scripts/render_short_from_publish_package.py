#!/usr/bin/env python3
"""
render_short_from_publish_package.py — local, free draft vertical-video renderer.

Turns a Nexus publish package (the script section) into a 1080x1920 draft MP4 using
Pillow (text slides) + ffmpeg (stitch). No paid APIs, no cloud, no upload, no posting.
This is the "video file" step in: package -> video file -> (approved) manual posting.

ffmpeg note: this host's ffmpeg has no drawtext (no libfreetype), so text is rendered
to PNG slides with Pillow, then concatenated by ffmpeg. Output is a DRAFT for review.

SAFETY: dry-run by default (slides only). --apply renders the MP4. Never uploads or posts.

Usage:
  python3 scripts/render_short_from_publish_package.py --package reports/publish_packages/fcf087ea_business_credit_myths.md --dry-run
  python3 scripts/render_short_from_publish_package.py --package reports/publish_packages/fcf087ea_business_credit_myths.md --apply
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "reports" / "tool_lab" / "renders"
W, H = 1080, 1920
BG_TOP, BG_BOT = (16, 22, 46), (32, 44, 92)   # dark navy gradient
FG = (245, 248, 255)
ACCENT = (120, 160, 255)
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
SEC_PER_SLIDE = 3.5


def extract_script(package_path: Path) -> list[str]:
    """Pull the 'Final short...script' section and split into slide chunks."""
    text = package_path.read_text(errors="ignore")
    m = re.search(r"##\s*Final[^\n]*\n(.*?)(?:\n##\s|\Z)", text, re.S | re.I)
    body = m.group(1).strip() if m else text
    # Split into lines, group HOOK/MYTH/CTA-style lines as individual slides
    chunks = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        chunks.append(line)
    # Merge stray short lines into the previous chunk
    merged: list[str] = []
    for c in chunks:
        if merged and len(c) < 18 and not re.match(r"(HOOK|MYTH|CTA|TIP)", c, re.I):
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged[:8]  # keep it short-form


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_slide(idx: int, text: str, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):  # vertical gradient
        t = y / H
        px_row = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = px_row
    d = ImageDraw.Draw(img)
    label = text.split(":", 1)[0] if ":" in text[:14].upper() and re.match(r"(HOOK|MYTH|CTA|TIP)", text, re.I) else ""
    main = text.split(":", 1)[1].strip() if label else text
    try:
        f_label = ImageFont.truetype(FONT_PATH, 56)
        f_main = ImageFont.truetype(FONT_PATH, 84)
        f_foot = ImageFont.truetype(FONT_PATH, 36)
    except Exception:
        f_label = f_main = f_foot = ImageFont.load_default()
    y = 360
    if label:
        d.text((90, y), label.upper(), font=f_label, fill=ACCENT)
        y += 110
    for ln in wrap(d, main, f_main, W - 180):
        d.text((90, y), ln, font=f_main, fill=FG)
        y += 104
    d.text((90, H - 150), f"{idx}/{total}  ·  Educational only — not advice", font=f_foot, fill=(150, 165, 200))
    return img


def main():
    ap = argparse.ArgumentParser(description="Render a draft vertical short from a publish package (local/free)")
    ap.add_argument("--package", required=True)
    ap.add_argument("--apply", action="store_true", help="Render MP4 (default: slides only / dry-run)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run

    pkg = Path(args.package)
    if not pkg.exists():
        print(f"! package not found: {pkg}")
        return
    stem = pkg.stem
    slides_dir = OUT_DIR / f"{stem}_slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    chunks = extract_script(pkg)
    print(f"Package: {pkg.name}")
    print(f"Slides: {len(chunks)} (~{SEC_PER_SLIDE}s each ≈ {len(chunks)*SEC_PER_SLIDE:.0f}s)")
    for i, c in enumerate(chunks, 1):
        img = render_slide(i, c, len(chunks))
        img.save(slides_dir / f"slide_{i:02d}.png")
    print(f"Slide PNGs: {slides_dir} ✓")

    if not apply:
        print("\nDRY-RUN — slides rendered, MP4 not built. Re-run with --apply to render the draft MP4.")
        print("Nothing uploaded or posted.")
        return

    if not shutil.which("ffmpeg"):
        print("! ffmpeg not found — cannot stitch MP4. Slides are ready for manual editing.")
        return
    # concat demuxer with per-image duration
    listing = slides_dir / "concat.txt"
    lines = []
    for i in range(1, len(chunks) + 1):
        lines.append(f"file '{slides_dir / f'slide_{i:02d}.png'}'")
        lines.append(f"duration {SEC_PER_SLIDE}")
    lines.append(f"file '{slides_dir / f'slide_{len(chunks):02d}.png'}'")  # last frame repeat
    listing.write_text("\n".join(lines))
    out_mp4 = OUT_DIR / f"{stem}_draft.mp4"
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
           "-vf", "scale=1080:1920,format=yuv420p", "-r", "30",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out_mp4)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode == 0 and out_mp4.exists():
        size = out_mp4.stat().st_size // 1024
        print(f"\nDraft MP4: {out_mp4} ({size} KB) ✓")
        print("This is a DRAFT for review. Nothing uploaded or posted. Add voiceover/B-roll before publishing if desired.")
    else:
        print("! ffmpeg failed:", (r.stderr or "")[-400:])


if __name__ == "__main__":
    main()
