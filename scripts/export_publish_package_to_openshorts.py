#!/usr/bin/env python3
"""
export_publish_package_to_openshorts.py — adapter: Nexus content -> OpenShorts project input.

Converts an approved Nexus creative-short plan (scenes.json + publish package) into an
OpenShorts-style "AI Shorts" project input JSON that OpenShorts could consume to render a
draft MP4. It does NOT install or run OpenShorts, does NOT post, and does NOT touch the
publisher gates. Output is local input files only.

Nexus gate contract (unchanged):
  * Nexus authors + approves content.
  * OpenShorts (if run by Ray) generates a DRAFT MP4 only — into its output/ dir.
  * scripts/social_publish_executor.py remains the ONLY upload path (approval-gated).
  * No public/external posting without Ray's per-item approval + executor enable.

SAFETY: dry-run by default; --apply only writes local input files. No network, no posting.

Usage:
  python3 scripts/export_publish_package_to_openshorts.py --scenes reports/creative_short_plans/fcf087ea_business_credit_myths_v2.scenes.json --apply
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tool-lab" / "openshorts_inputs"


def to_openshorts_project(plan: dict) -> dict:
    """Map Nexus scenes -> a generic OpenShorts 'AI Shorts' project input.
    NOTE: exact field names may need tuning against the installed OpenShorts version;
    this is a faithful, documented mapping, not a guaranteed schema match."""
    yt = plan.get("youtube", {})
    return {
        "_nexus": {
            "content_id": plan.get("content_id"),
            "source": "nexus_creative_plan",
            "publish_gate": "social_publish_executor.py only — OpenShorts must NOT post",
            "disclosure_required": True,
        },
        "project": {
            "title": plan.get("title"),
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "target_seconds": plan.get("target_seconds", "30-45"),
            "voice": plan.get("voice"),
            "voice_tone": plan.get("voice_tone"),
            "music_mood": plan.get("music_mood"),
            "captions": True,
            "watermark": False,
            "publish": False,            # explicit: never auto-publish from OpenShorts
        },
        "script": {
            "full_voiceover": " ".join(s.get("vo", "") for s in plan.get("scenes", [])),
            "disclosure": plan.get("disclosure"),
        },
        "scenes": [
            {
                "index": s["id"],
                "label": s.get("label"),
                "narration": s.get("vo"),
                "on_screen_text": s.get("onscreen"),
                "caption": s.get("caption"),
                "visual_prompt": s.get("visual"),
                "motion": s.get("motion"),
                "bg_theme": s.get("bg"),
            } for s in plan.get("scenes", [])
        ],
        "youtube_metadata": {
            "title": yt.get("title"),
            "description": yt.get("description"),
            "hashtags": yt.get("hashtags", []),
            "privacy_on_export": "none (export MP4 only; do not publish)",
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Export Nexus plan -> OpenShorts project input (no posting)")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--apply", action="store_true", help="Write the input files (default: dry-run preview)")
    args = ap.parse_args()

    plan = json.loads(Path(args.scenes).read_text())
    project = to_openshorts_project(plan)
    stem = Path(args.scenes).name.replace(".scenes.json", "")
    print(f"Nexus -> OpenShorts adapter for: {plan.get('title')}")
    print(f"scenes: {len(project['scenes'])} · publish flag: {project['project']['publish']} (never auto-post)")

    if not args.apply:
        print("\nDRY-RUN — no files written. Preview of project input:")
        print(json.dumps(project, indent=2)[:900] + "\n...")
        print("\nRe-run with --apply to write the OpenShorts input JSON locally.")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{stem}.openshorts.json"
    out.write_text(json.dumps(project, indent=2))
    print(f"\nwrote: {out}")
    print("This is INPUT only. OpenShorts is not installed/run here. If Ray runs OpenShorts later,")
    print("feed this as the AI-Shorts project, export the MP4 to output/, and review it.")
    print("Publishing still goes through social_publish_executor.py with Ray approval. No posting done.")


if __name__ == "__main__":
    main()
