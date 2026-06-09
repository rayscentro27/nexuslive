#!/usr/bin/env python3
"""
export_publish_package_to_short_video_maker.py — Nexus plan -> Short Video Maker request.

Short Video Maker (gyoridavid/short-video-maker, MIT) renders 9:16 shorts from text using
local Kokoro TTS + Whisper captions + Pexels background video + Remotion. It has NO
auto-publish. This adapter maps a Nexus creative plan to its REST body
(POST /api/short-video) and writes a local JSON. It does NOT call the API, install, or post.

SAFETY: dry-run by default; --apply writes a local JSON only. No network, no posting.
Requires a FREE Pexels API key at render time (Ray provides) — never embedded here.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tool-lab" / "short_video_maker_inputs"

# Map a scene's theme/visual to safe Pexels background search terms (business explainer).
def search_terms(scene: dict) -> list[str]:
    txt = f"{scene.get('label','')} {scene.get('visual','')} {scene.get('onscreen','')}".lower()
    terms = []
    if "myth" in txt: terms = ["business meeting", "office", "confused"]
    elif "truth" in txt: terms = ["business growth", "finance", "documents"]
    elif "cta" in txt: terms = ["entrepreneur", "laptop", "city"]
    else: terms = ["business", "office", "finance"]
    return terms[:3]


def to_svm_request(plan: dict) -> dict:
    scenes = [{"text": s.get("vo", ""), "searchTerms": search_terms(s)} for s in plan.get("scenes", [])]
    return {
        "_nexus": {
            "content_id": plan.get("content_id"),
            "publish_gate": "social_publish_executor.py only — SVM has no publishing; never auto-post",
            "disclosure_required": True,
            "note": "SVM renders MP4 only; add disclosure overlay/description before any upload",
        },
        "scenes": scenes,
        "config": {
            "orientation": "portrait",            # 9:16 for Shorts
            "voice": "bm_lewis",                  # Kokoro local voice (free); swap as desired
            "captionPosition": "center",
            "captionBackgroundColor": "#1A2244",  # Nexus navy
            "music": "uneasy",                    # SVM built-in royalty-free bed; or "" for none
            "musicVolume": "low",
            "paddingBack": 1500,
        },
        "youtube_metadata": plan.get("youtube", {}),
        "disclosure": plan.get("disclosure"),
    }


def main():
    ap = argparse.ArgumentParser(description="Export Nexus plan -> Short Video Maker request (no posting)")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    plan = json.loads(Path(args.scenes).read_text())
    body = to_svm_request(plan)
    print(f"Nexus -> Short Video Maker adapter: {plan.get('title')}")
    print(f"scenes: {len(body['scenes'])} · orientation: {body['config']['orientation']} · voice: {body['config']['voice']}")
    print("Render needs: SVM running locally + a FREE Pexels API key (Ray provides at render time).")
    if not args.apply:
        print("\nDRY-RUN — no file written. Preview:")
        print(json.dumps(body, indent=2)[:700] + "\n...")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    stem = Path(args.scenes).name.replace(".scenes.json", "")
    out = OUT / f"{stem}.svm.json"
    out.write_text(json.dumps(body, indent=2))
    print(f"\nwrote: {out}")
    print("POST this to a LOCAL Short Video Maker (http://localhost:3123/api/short-video) to render a draft.")
    print("Publishing still goes through social_publish_executor.py with Ray approval. No posting done here.")


if __name__ == "__main__":
    main()
