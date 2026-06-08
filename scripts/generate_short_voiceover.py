#!/usr/bin/env python3
"""
generate_short_voiceover.py — local/free voiceover for a creative short.

Reads a scenes.json plan and generates one WAV per scene + a concatenated full WAV.
TTS engine preference: Piper (if installed) -> macOS `say` (local, free) -> blocked.
No paid APIs. No network. Nothing faked — if no local TTS exists, it reports blocked.

Output: reports/tool_lab/creative_renders/<stem>_voiceover_v2.wav (+ per-scene wavs)
        and a <stem>_voiceover_timing.json with per-scene durations (for the renderer).
"""
from __future__ import annotations
import argparse, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "tool_lab" / "creative_renders"


def have(cmd): return shutil.which(cmd) is not None


def ffprobe_dur(path: Path) -> float:
    if not have("ffprobe"):
        return 0.0
    try:
        out = subprocess.run(["ffprobe","-v","quiet","-of","csv=p=0","-show_entries","format=duration",str(path)],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return float(out) if out else 0.0
    except Exception:
        return 0.0


def tts_say(text: str, out_wav: Path, voice: str) -> bool:
    """macOS `say` -> AIFF -> wav via ffmpeg. Local, free."""
    aiff = out_wav.with_suffix(".aiff")
    try:
        subprocess.run(["say","-v",voice,"-o",str(aiff),text], check=True, timeout=60)
    except Exception:
        try:
            subprocess.run(["say","-o",str(aiff),text], check=True, timeout=60)  # default voice
        except Exception:
            return False
    if have("ffmpeg"):
        subprocess.run(["ffmpeg","-y","-i",str(aiff),"-ar","44100","-ac","2",str(out_wav)],
                       capture_output=True, timeout=60)
        aiff.unlink(missing_ok=True)
        return out_wav.exists()
    return aiff.exists()


def tts_piper(text: str, out_wav: Path, model: str | None) -> bool:
    if not have("piper") or not model:
        return False
    try:
        p = subprocess.run(["piper","--model",model,"--output_file",str(out_wav)],
                           input=text, capture_output=True, text=True, timeout=120)
        return out_wav.exists() and p.returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Generate local voiceover for a creative short")
    ap.add_argument("--scenes", required=True, help="path to *.scenes.json")
    ap.add_argument("--piper-model", default=None, help="path to a Piper .onnx voice (optional)")
    args = ap.parse_args()

    plan = json.loads(Path(args.scenes).read_text())
    voice = plan.get("voice", "Daniel")
    scenes = plan["scenes"]
    OUT.mkdir(parents=True, exist_ok=True)
    stem = Path(args.scenes).name.replace(".scenes.json", "")

    engine = "piper" if (have("piper") and args.piper_model) else ("say" if have("say") else None)
    print(f"TTS engine: {engine or 'NONE (blocked)'}")
    if not engine:
        print("! No local TTS available (Piper not installed, macOS `say` missing). Voiceover BLOCKED.")
        print("  Script text is in the plan; generate VO manually or install Piper. No paid API used.")
        return 2

    timing = []
    per_scene_wavs = []
    for s in scenes:
        w = OUT / f"{stem}_s{s['id']:02d}.wav"
        ok = (tts_piper(s["vo"], w, args.piper_model) if engine == "piper"
              else tts_say(s["vo"], w, voice))
        dur = ffprobe_dur(w) if ok else 0.0
        # pad short lines a touch for readability/pacing
        dur = max(dur, 2.2) if ok else 3.0
        timing.append({"id": s["id"], "wav": str(w) if ok else None, "duration": round(dur, 2)})
        if ok:
            per_scene_wavs.append(w)
        print(f"  scene {s['id']:02d}: {'ok' if ok else 'FAILED'}  dur={dur:.2f}s")

    # concat full voiceover
    full = OUT / f"{stem}_voiceover_v2.wav"
    if per_scene_wavs and have("ffmpeg"):
        listing = OUT / f"{stem}_vo_concat.txt"
        listing.write_text("\n".join(f"file '{w}'" for w in per_scene_wavs))
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),"-c","copy",str(full)],
                       capture_output=True, timeout=120)
        if not full.exists():  # fallback re-encode
            subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),str(full)],
                           capture_output=True, timeout=120)
    timing_path = OUT / f"{stem}_voiceover_timing.json"
    timing_path.write_text(json.dumps({"engine": engine, "voice": voice, "scenes": timing}, indent=2))
    total = sum(t["duration"] for t in timing)
    print(f"\nfull voiceover: {full if full.exists() else '(per-scene only)'}")
    print(f"timing: {timing_path}  total ~{total:.1f}s  engine={engine}")
    print("Local/free TTS only. No paid API, no network, nothing uploaded.")


if __name__ == "__main__":
    main()
