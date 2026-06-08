#!/usr/bin/env python3
"""
render_creative_short_remotion.py — Nexus Creative Shorts Engine v1 renderer.

Two engines:
  --engine local     (default) Pillow branded scenes + ffmpeg motion (zoompan) +
                     per-scene voiceover mux. Fully local/free, works now.
  --engine remotion  Renders via a Remotion project in tool-lab/remotion-shorts/.
                     If that project isn't set up, it exits with setup steps (no fake output).

Consumes: a *.scenes.json (from create_creative_short_plan.py) and, if present, the
voiceover timing json (from generate_short_voiceover.py) for per-scene durations + audio.

NO upload, NO posting, NO paid APIs. Output is a DRAFT MP4 for review.
Output: reports/tool_lab/creative_renders/<stem>.mp4
"""
from __future__ import annotations
import argparse, json, math, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "tool_lab" / "creative_renders"
W, H = 1080, 1920
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

THEMES = {
    "navy":   ((16,22,46),(32,44,92),(120,160,255)),
    "maroon": ((58,16,26),(112,28,44),(255,120,135)),
    "green":  ((12,44,30),(22,84,56),(120,235,170)),
}


def have(c): return shutil.which(c) is not None


def font(sz, bold=True):
    try:
        return ImageFont.truetype(FONT_BOLD if bold and Path(FONT_BOLD).exists() else FONT, sz)
    except Exception:
        return ImageFont.load_default()


def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur+" "+w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def render_scene(scene, idx, total, disclosure):
    top, bot, accent = THEMES.get(scene.get("bg","navy"), THEMES["navy"])
    img = Image.new("RGB",(W,H)); px = img.load()
    for y in range(H):
        t=y/H; row=tuple(int(top[i]+(bot[i]-top[i])*t) for i in range(3))
        for x in range(W): px[x,y]=row
    d = ImageDraw.Draw(img)
    # label chip
    label = scene.get("label","")
    if label:
        f_l = font(46)
        tw = d.textlength(label, font=f_l)
        d.rounded_rectangle([90,300,90+tw+56,300+86], radius=24, fill=accent)
        d.text((118,318), label, font=f_l, fill=(12,16,32))
    # main on-screen text (big, centered block)
    f_m = font(96)
    main = scene.get("onscreen","")
    lines = wrap(d, main, f_m, W-180)
    y = 560
    for ln in lines:
        lw = d.textlength(ln, font=f_m)
        d.text(((W-lw)//2, y), ln, font=f_m, fill=(245,248,255)); y += 116
    # visual hint (subtle, smaller)
    f_v = font(40, bold=False)
    for ln in wrap(d, scene.get("visual",""), f_v, W-220)[:2]:
        lw=d.textlength(ln,font=f_v); d.text(((W-lw)//2,y+30), ln, font=f_v, fill=accent); y+=52
    # caption bottom
    f_c = font(48)
    cap = scene.get("caption","")
    for ln in wrap(d, cap, f_c, W-160):
        lw=d.textlength(ln,font=f_c); d.text(((W-lw)//2, H-360), ln, font=f_c, fill=(225,232,250))
    # footer + scene counter
    f_f = font(32, bold=False)
    d.text((90, H-150), f"{idx}/{total}", font=f_f, fill=(150,165,200))
    foot = disclosure if scene.get("label")=="CTA" else "Educational only — not financial advice"
    for ln in wrap(d, foot, f_f, W-180)[:3]:
        d.text((90, H-110), ln, font=f_f, fill=(150,165,200));
    return img


def clip_from_image(png: Path, dur: float, motion: str, out: Path):
    frames = max(int(round(dur*30)), 30)
    if motion == "zoom_out":
        z = f"if(eq(on,0),1.12,max(zoom-0.0009,1.0))"
    elif motion == "slide_left":
        z = "1.06"
    else:  # zoom_in / default
        z = "min(zoom+0.0010,1.12)"
    vf = (f"scale=1300:2311,zoompan=z='{z}':d={frames}:s={W}x{H}:fps=30,"
          f"fade=t=in:st=0:d=0.25,format=yuv420p")
    cmd=["ffmpeg","-y","-loop","1","-i",str(png),"-t",f"{dur:.2f}","-r","30","-vf",vf,
         "-c:v","libx264","-preset","medium","-crf","20",str(out)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180)


def render_local(plan, timing, stem):
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = plan["scenes"]; total=len(scenes)
    dur_by = {t["id"]: t["duration"] for t in (timing.get("scenes",[]) if timing else [])}
    wav_by = {t["id"]: t.get("wav") for t in (timing.get("scenes",[]) if timing else [])}
    clips=[]
    for i,s in enumerate(scenes,1):
        png = OUT/f"{stem}_s{s['id']:02d}.png"
        render_scene(s,i,total,plan.get("disclosure","")).save(png)
        dur = dur_by.get(s["id"], 4.0)
        clip = OUT/f"{stem}_clip_{s['id']:02d}.mp4"
        r = clip_from_image(png, dur, s.get("motion","zoom_in"), clip)
        if r.returncode!=0 or not clip.exists():
            print(f"  ! scene {s['id']} clip failed: {(r.stderr or '')[-200:]}"); return None
        clips.append(clip)
        print(f"  scene {s['id']:02d} clip ok ({dur:.1f}s, {s.get('motion')})")
    # concat video
    listing=OUT/f"{stem}_clips.txt"; listing.write_text("\n".join(f"file '{c}'" for c in clips))
    silent=OUT/f"{stem}_silent.mp4"
    r=subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),"-c","copy",str(silent)],capture_output=True,text=True,timeout=180)
    if not silent.exists():
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),str(silent)],capture_output=True,timeout=180)
    # mux voiceover if available
    vo = OUT/f"{stem}_voiceover_v2.wav"
    final=OUT/f"{stem}.mp4"
    if vo.exists():
        subprocess.run(["ffmpeg","-y","-i",str(silent),"-i",str(vo),"-c:v","copy","-c:a","aac","-b:a","160k","-shortest",str(final)],capture_output=True,timeout=180)
        audio="voiceover muxed"
    else:
        shutil.copy(silent, final); audio="NO voiceover (run generate_short_voiceover.py first)"
    return final, audio


def main():
    ap=argparse.ArgumentParser(description="Render a creative short (local engine works now; remotion optional)")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--engine", choices=["local","remotion"], default="local")
    args=ap.parse_args()
    plan=json.loads(Path(args.scenes).read_text())
    stem=Path(args.scenes).name.replace(".scenes.json","")
    timing_path=OUT/f"{stem}_voiceover_timing.json"
    timing=json.loads(timing_path.read_text()) if timing_path.exists() else None

    if args.engine=="remotion":
        proj=ROOT/"tool-lab"/"remotion-shorts"
        if not (proj/"package.json").exists():
            print("Remotion engine selected but tool-lab/remotion-shorts is not set up.")
            print("Setup (local, no paid API):")
            print("  cd tool-lab/remotion-shorts && npm i remotion @remotion/cli @remotion/renderer")
            print("  (first render downloads a headless Chromium — heavy; evaluate before relying on it)")
            print("No fake output produced. Use --engine local for a working draft now.")
            return 3
        if not (proj/"node_modules").exists():
            print("Remotion deps not installed. Run: cd tool-lab/remotion-shorts && npm install")
            return 3
        out_mp4 = OUT/f"{stem}_remotion.mp4"
        OUT.mkdir(parents=True, exist_ok=True)
        print(f"Rendering via Remotion (npx remotion render NexusShort) → {out_mp4}")
        cmd = ["npx","remotion","render","NexusShort", str((OUT/f"{stem}_remotion.mp4").resolve())]
        r = subprocess.run(cmd, cwd=str(proj), capture_output=True, text=True, timeout=1200)
        ok = out_mp4.exists()
        print((r.stdout or "")[-500:])
        if not ok:
            print("! Remotion render did not produce output:", (r.stderr or "")[-600:])
            print("  (First render downloads a headless Chromium — may be the blocker.) Use --engine local meanwhile.")
            return 4
        print(f"\n✓ Remotion draft: {out_mp4} ({out_mp4.stat().st_size//1024} KB)")
        print("DRAFT for review. Nothing uploaded or posted.")
        return 0

    if not have("ffmpeg"):
        print("! ffmpeg required for local engine."); return 2
    print(f"Rendering creative short (local engine): {stem}  scenes={len(plan['scenes'])}  vo={'yes' if timing else 'no'}")
    res=render_local(plan, timing, stem)
    if not res:
        print("! render failed — see errors above."); return 4
    final, audio = res
    size = final.stat().st_size//1024 if final.exists() else 0
    print(f"\n✓ Creative draft: {final} ({size} KB) · audio: {audio}")
    print("DRAFT for review. Nothing uploaded or posted. Music: placeholder/none (add YouTube Audio Library track in edit).")


if __name__ == "__main__":
    main()
