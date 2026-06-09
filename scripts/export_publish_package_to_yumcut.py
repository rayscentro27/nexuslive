#!/usr/bin/env python3
"""
export_publish_package_to_yumcut.py — adapter: Nexus plan -> YumCut-style project input.

NOTE: YumCut (github.com/IgorShadurin/app.yumcut.com) is licensed PolyForm **Noncommercial**
and is a paid SaaS (Stripe/Runware) with built-in auto-publishing — so it is REJECTED for
adoption by Nexus (a commercial/revenue operation). This adapter is a DESIGN artifact only:
it shows how Nexus content WOULD map to a prompt-to-short tool, and emits a local input file.
It does NOT install/run YumCut, never posts, never spends money.

SAFETY: dry-run by default; --apply writes a local JSON only. No network, no posting.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tool-lab" / "yumcut_inputs"


def to_yumcut_project(plan: dict) -> dict:
    yt = plan.get("youtube", {})
    return {
        "_nexus": {
            "content_id": plan.get("content_id"),
            "adoption_status": "REJECTED (PolyForm Noncommercial license + paid APIs + auto-publish)",
            "publish_gate": "social_publish_executor.py only — tool must NOT post",
            "disclosure_required": True,
        },
        "project": {
            "title": plan.get("title"),
            "format": "vertical", "aspect_ratio": "9:16", "resolution": "1080x1920",
            "target_seconds": plan.get("target_seconds", "30-45"),
            "voice": plan.get("voice"), "voice_tone": plan.get("voice_tone"),
            "music_mood": plan.get("music_mood"),
            "captions": True, "publish": False,   # never auto-publish
        },
        "prompt": " ".join(s.get("vo", "") for s in plan.get("scenes", [])),
        "scenes": [
            {"index": s["id"], "label": s.get("label"), "narration": s.get("vo"),
             "on_screen_text": s.get("onscreen"), "caption": s.get("caption"),
             "visual_prompt": s.get("visual"), "motion": s.get("motion")}
            for s in plan.get("scenes", [])
        ],
        "disclosure": plan.get("disclosure"),
        "youtube_metadata": {"title": yt.get("title"), "description": yt.get("description"),
                             "hashtags": yt.get("hashtags", []),
                             "privacy_on_export": "none (export MP4 only; do not publish)"},
    }


def main():
    ap = argparse.ArgumentParser(description="Export Nexus plan -> YumCut project input (design-only; no posting)")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    plan = json.loads(Path(args.scenes).read_text())
    project = to_yumcut_project(plan)
    print("Nexus -> YumCut adapter (DESIGN ONLY — YumCut adoption REJECTED on license/paid/auto-publish)")
    print(f"title: {plan.get('title')} · scenes: {len(project['scenes'])} · publish: {project['project']['publish']}")
    if not args.apply:
        print("\nDRY-RUN — no file written. Preview:")
        print(json.dumps(project, indent=2)[:700] + "\n...")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    stem = Path(args.scenes).name.replace(".scenes.json", "")
    out = OUT / f"{stem}.yumcut.json"
    out.write_text(json.dumps(project, indent=2))
    print(f"\nwrote: {out}")
    print("Input only. YumCut not installed/run (noncommercial license + paid APIs).")
    print("Publishing still goes through social_publish_executor.py with Ray approval. No posting done.")


if __name__ == "__main__":
    main()
