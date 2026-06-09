#!/usr/bin/env python3
"""
export_creative_plan_to_hyperframes.py — Nexus creative plan -> HyperFrames HTML composition.

Turns a Nexus `*.scenes.json` (create_creative_short_plan.py) + a voiceover timing json
(generate_short_voiceover.py) into a single self-contained HyperFrames `index.html`
composition (HTML/CSS/JS, GSAP-driven, seekable) that HyperFrames can render to MP4.

INPUT  (Nexus owns all of this — research, script, scoring, approvals):
  --scenes   path to *.scenes.json  (scene list, onscreen text, captions, vo, bg/accent/motion)
  --timing   path to *_voiceover_timing.json (per-scene durations; optional — falls back to 4s)
  --audio    voiceover wav/mp3 (copied into the project as voiceover.wav)
  --outdir   HyperFrames project dir (default tool-lab/hyperframes-shorts)

OUTPUT (draft only — NEVER posts/uploads/schedules):
  <outdir>/index.html         self-contained composition
  <outdir>/voiceover.wav       copied audio track (if --audio given)
  <outdir>/composition.json    the resolved scene/timing data (for inspection/CI)

SAFETY: no network, no posting, no credentials. social_publish_executor.py remains the
only upload path; Ray approval remains required for any publish/schedule/public action.
"""
from __future__ import annotations
import argparse, json, shutil, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
W, H = 1080, 1920  # 9:16 portrait Shorts

# Nexus palette (matches creative_short_plan style lock)
PALETTE = {
    "navy":   "#1A2244",
    "blue":   "#5B7CFA",
    "maroon": "#5A1A22",
    "red":    "#FF4D4D",
    "green":  "#1F7A4D",
    "success":"#27D17F",
    "ink":    "#0C1024",
    "paper":  "#F4F6FF",
}

def bg_gradient(bg: str, accent: str) -> str:
    base = PALETTE.get(bg, PALETTE["navy"])
    acc = PALETTE.get(accent, PALETTE["blue"])
    return f"radial-gradient(120% 90% at 50% 18%, {acc}22 0%, {base} 55%, {PALETTE['ink']} 100%)"


def kind_of(label: str) -> str:
    l = (label or "").upper()
    if "MYTH" in l: return "myth"
    if "TRUTH" in l: return "truth"
    if "HOOK" in l: return "hook"
    if "CTA" in l: return "cta"
    return "default"


def resolve(scenes_path: Path, timing_path: Path | None) -> dict:
    plan = json.loads(scenes_path.read_text())
    timing = {}
    if timing_path and timing_path.exists():
        timing = {t["id"]: float(t["duration"]) for t in json.loads(timing_path.read_text()).get("scenes", [])}
    scenes, cursor = [], 0.0
    for s in plan["scenes"]:
        dur = timing.get(s["id"], 4.0)
        scenes.append({
            "id": s["id"], "label": s.get("label", ""),
            "onscreen": s.get("onscreen", ""), "caption": s.get("caption", ""),
            "vo": s.get("vo", ""), "visual": s.get("visual", ""),
            "bg": s.get("bg", "navy"), "accent": s.get("accent", "blue"),
            "motion": s.get("motion", "zoom_in"), "kind": kind_of(s.get("label", "")),
            "start": round(cursor, 3), "duration": round(dur, 3),
        })
        cursor += dur
    return {
        "content_id": plan.get("content_id"), "title": plan.get("title"),
        "platform": plan.get("platform", "YouTube Shorts"),
        "disclosure": plan.get("disclosure", "Educational only — not financial advice."),
        "brand": "NEXUS · GoClearOnline",
        "youtube": plan.get("youtube", {}),
        "fps": FPS, "width": W, "height": H,
        "total": round(cursor, 3), "scenes": scenes,
    }


def render_html(data: dict, audio_name: str | None) -> str:
    comp_id = "main"  # HyperFrames scaffold convention; window.__timelines["main"]
    content_short = (data.get("content_id") or "short").split("-")[0]
    total_dur = data["total"]
    e = lambda s: html.escape(str(s or ""))

    scene_divs, tl_js = [], []
    for s in data["scenes"]:
        sid, start, dur, kind = s["id"], s["start"], s["duration"], s["kind"]
        grad = bg_gradient(s["bg"], s["accent"])
        accent = PALETTE.get(s["accent"], PALETTE["blue"])
        badge = {"myth": "MYTH", "truth": "TRUTH", "hook": "", "cta": ""}.get(kind, "")
        badge_html = f'<div class="badge badge-{kind}">{e(badge)}</div>' if badge else ""
        mark = ""
        if kind == "myth":
            mark = '<div class="stamp stamp-x">✕</div>'
        elif kind == "truth":
            mark = '<div class="stamp stamp-ok">✓</div>'
        scene_divs.append(f'''
    <section class="scene clip scene-{kind}" id="s{sid}" data-start="{start}" data-duration="{dur}" data-track-index="0"
             style="background:{grad};">
      {badge_html}
      <h1 class="onscreen">{e(s['onscreen'])}</h1>
      {mark}
      <div class="accentbar" style="background:{accent};"></div>
    </section>''')
        # kinetic caption (own track so it reads as "fast captions")
        scene_divs.append(
            f'    <div class="caption clip" id="c{sid}" data-start="{start}" data-duration="{dur}" data-track-index="1">{e(s["caption"])}</div>'
        )
        # seekable GSAP segment per scene
        tl_js.append(f"""
    // scene {sid} ({kind})
    tl.set('#s{sid}', {{opacity:0}}, {start});
    tl.set('#c{sid}', {{opacity:0, y:24}}, {start});
    tl.to('#s{sid}', {{opacity:1, duration:0.25}}, {start});
    tl.fromTo('#s{sid} .onscreen', {{opacity:0, scale:0.82, y:{ -30 if kind=='truth' else 30}}},
              {{opacity:1, scale:1, y:0, duration:0.55, ease:'back.out(1.6)'}}, {start});
    tl.to('#s{sid} .accentbar', {{scaleX:1, duration:0.5, ease:'power2.out'}}, {start+0.1});
    tl.to('#c{sid}', {{opacity:1, y:0, duration:0.3}}, {start+0.15});
    {f"tl.fromTo('#s{sid} .stamp', {{opacity:0, scale:1.8, rotate:-12}}, {{opacity:1, scale:1, rotate:-8, duration:0.35, ease:'back.out(2)'}}, {start+0.2});" if kind in ('myth','truth') else ""}
    tl.to(['#s{sid}','#c{sid}'], {{opacity:0, duration:0.2}}, {round(start+dur-0.2,3)});
    tl.set(['#s{sid}','#c{sid}'], {{opacity:0}}, {round(start+dur,3)});""")

    audio_el = (f'\n    <audio id="vo" data-start="0" data-duration="{total_dur}" data-track-index="9" '
                f'data-volume="1" src="{audio_name}"></audio>' if audio_name else "")
    disclosure = e(data["disclosure"])
    brand = e(data["brand"])
    title = e(data["title"])

    return f'''<!doctype html>
<html lang="en" data-resolution="portrait">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{title} — HyperFrames draft ({content_short})</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ width:{W}px; height:{H}px; overflow:hidden; background:{PALETTE['ink']};
    font-family:'Inter','Helvetica Neue',Arial,sans-serif; color:{PALETTE['paper']}; }}
  #stage {{ position:relative; width:{W}px; height:{H}px; }}
  .scene {{ position:absolute; inset:0; display:flex; flex-direction:column;
    align-items:center; justify-content:center; padding:120px 90px; opacity:0; }}
  .onscreen {{ font-size:108px; line-height:1.05; font-weight:900; text-align:center;
    letter-spacing:-2px; text-shadow:0 8px 40px #0008; max-width:900px; }}
  .scene-myth .onscreen {{ color:#FFE3E3; }}
  .scene-truth .onscreen {{ color:#DDFBEC; }}
  .badge {{ position:absolute; top:300px; font-size:46px; font-weight:900; letter-spacing:8px;
    padding:16px 40px; border-radius:999px; }}
  .badge-myth {{ background:{PALETTE['red']}; color:#fff; }}
  .badge-truth {{ background:{PALETTE['success']}; color:{PALETTE['ink']}; }}
  .accentbar {{ position:absolute; bottom:560px; height:14px; width:360px; border-radius:8px;
    transform:scaleX(0); transform-origin:center; }}
  .stamp {{ position:absolute; top:230px; right:140px; font-size:170px; font-weight:900;
    opacity:0; text-shadow:0 6px 24px #0009; }}
  .stamp-x {{ color:{PALETTE['red']}; }}
  .stamp-ok {{ color:{PALETTE['success']}; }}
  .caption {{ position:absolute; left:60px; right:60px; bottom:240px; text-align:center;
    font-size:58px; font-weight:800; line-height:1.2; opacity:0;
    background:#0009; padding:24px 30px; border-radius:24px; backdrop-filter:blur(2px); }}
  .brand {{ position:absolute; top:90px; left:0; right:0; text-align:center;
    font-size:34px; font-weight:800; letter-spacing:6px; color:{PALETTE['blue']}; opacity:0.92; }}
  .disclosure {{ position:absolute; bottom:120px; left:0; right:0; text-align:center;
    font-size:30px; font-weight:600; color:#cdd6ff; opacity:0.85; }}
</style>
</head>
<body>
  <div id="root" data-composition-id="{comp_id}" data-start="0"
       data-duration="{total_dur}" data-width="{W}" data-height="{H}" data-fps="{FPS}">
    <div class="brand clip" data-start="0" data-duration="{total_dur}" data-track-index="2">{brand}</div>
{''.join(scene_divs)}
    <div class="disclosure clip" data-start="0" data-duration="{total_dur}" data-track-index="3">{disclosure}</div>{audio_el}

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{''.join(tl_js)}
      window.__timelines = window.__timelines || {{}};
      window.__timelines['{comp_id}'] = tl;
    </script>
  </div>
</body>
</html>'''


def main():
    ap = argparse.ArgumentParser(description="Export Nexus creative plan -> HyperFrames composition")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--timing", default=None)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--outdir", default=str(ROOT / "tool-lab" / "hyperframes-shorts"))
    args = ap.parse_args()

    scenes_path = Path(args.scenes)
    timing_path = Path(args.timing) if args.timing else None
    if not timing_path:
        stem = scenes_path.name.replace(".scenes.json", "")
        cand = ROOT / "reports" / "tool_lab" / "creative_renders" / f"{stem}_voiceover_timing.json"
        timing_path = cand if cand.exists() else None

    data = resolve(scenes_path, timing_path)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audio_name = None
    if args.audio:
        src = Path(args.audio)
        audio_name = "voiceover" + src.suffix.lower()
        shutil.copyfile(src, outdir / audio_name)

    (outdir / "composition.json").write_text(json.dumps(data, indent=2))
    (outdir / "index.html").write_text(render_html(data, audio_name))

    print(f"wrote: {outdir/'index.html'}")
    print(f"scenes: {len(data['scenes'])} · total: {data['total']}s @ {FPS}fps · audio: {audio_name or 'none'}")
    print(f"composition data: {outdir/'composition.json'}")
    print("next: npx hyperframes render -c index.html -o <out>.mp4  (DRAFT ONLY — no upload)")


if __name__ == "__main__":
    main()
