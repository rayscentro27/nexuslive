#!/usr/bin/env python3
"""
create_creative_short_plan.py — author a Nexus Creative Short plan (v2).

Emits BOTH a human storyboard (.md) and a machine scene file (.scenes.json) that the
creative renderer + voiceover generator consume. Ships a hand-crafted storyboard for
content_id fcf087ea (3 Business Credit Myths) — myth-vs-truth structure, fast mobile pacing,
educational only, disclosure included. No upload, no posting.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / "reports" / "creative_short_plans"

DISCLOSURE = ("This content may include affiliate links. If you use a link, "
              "Nexus/GoClearOnline may earn a commission at no extra cost to you.")

# Built-in high-quality storyboard for fcf087ea
FCF087EA = {
    "content_id": "fcf087ea-cf90-43cd-85fe-40bd96d58e3f",
    "title": "3 Business Credit Myths That Cost You Time",
    "platform": "YouTube Shorts",
    "privacy_default": "unlisted",
    "voice": "Daniel",            # macOS 'say' voice (local/free); Piper voice if available
    "voice_tone": "confident, friendly, fast — like a sharp friend who knows funding",
    "music_mood": "light upbeat corporate / lo-fi business (use YouTube Audio Library, no copyright)",
    "target_seconds": "30-45",
    "youtube": {
        "title": "3 Business Credit Myths That Cost You Time #Shorts",
        "description": ("Three business credit myths that quietly cost people time and money — "
                        "and what actually works.\n\nEducational only — not financial advice. No guarantees.\n\n"
                        + DISCLOSURE + "\n\n#businesscredit #businessfunding #smallbusiness #entrepreneur #credittips"),
        "hashtags": ["Shorts","businesscredit","businessfunding","smallbusiness","entrepreneur","credittips","paydex","fundingreadiness"],
    },
    "disclosure": DISCLOSURE,
    "scenes": [
        {"id":1,"label":"HOOK","bg":"navy","accent":"blue","motion":"zoom_in",
         "onscreen":"3 BUSINESS CREDIT MYTHS","caption":"3 myths that cost you time",
         "vo":"Three business credit myths that are quietly costing you time and money.",
         "visual":"Bold title card, Nexus blue underline, small stickman pointing up"},
        {"id":2,"label":"MYTH 1","bg":"maroon","accent":"red","motion":"slide_left",
         "onscreen":"MYTH: \"You need revenue first\"","caption":"Myth 1: revenue first",
         "vo":"Myth one: you need revenue first.",
         "visual":"Red myth card, stickman shrugging, big X stamp"},
        {"id":3,"label":"TRUTH 1","bg":"green","accent":"green","motion":"zoom_in",
         "onscreen":"TRUTH: Structure first","caption":"Truth: structure first",
         "vo":"Truth: you need structure first. Entity, business bank account, and accounts that actually report.",
         "visual":"Green truth card, checkmark, 3 mini icons: entity, bank, report"},
        {"id":4,"label":"MYTH 2","bg":"maroon","accent":"red","motion":"slide_left",
         "onscreen":"MYTH: \"One card builds it\"","caption":"Myth 2: one card",
         "vo":"Myth two: one credit card builds your business credit.",
         "visual":"Single card icon with X, stickman confused"},
        {"id":5,"label":"TRUTH 2","bg":"green","accent":"green","motion":"zoom_in",
         "onscreen":"TRUTH: Bureaus want a pattern","caption":"Truth: a pattern, not one account",
         "vo":"Truth: bureaus want a pattern, not a single account. A few reporting accounts paid early beats one card.",
         "visual":"Multiple cards forming a rising bar chart"},
        {"id":6,"label":"MYTH 3","bg":"maroon","accent":"red","motion":"slide_left",
         "onscreen":"MYTH: \"It's fast\"","caption":"Myth 3: it's fast",
         "vo":"Myth three: it's fast.",
         "visual":"Stopwatch with X, stickman tapping foot"},
        {"id":7,"label":"TRUTH 3","bg":"green","accent":"green","motion":"zoom_in",
         "onscreen":"TRUTH: It takes cycles","caption":"Truth: it takes reporting cycles",
         "vo":"Truth: real reporting takes cycles. Anyone promising instant results is selling something.",
         "visual":"Calendar pages flipping, steady upward arrow"},
        {"id":8,"label":"CTA","bg":"navy","accent":"blue","motion":"zoom_out",
         "onscreen":"Save this. Build it right.","caption":"Educational only — not advice",
         "vo":"Save this, and build it the boring, correct way. Follow for more.",
         "visual":"Nexus wordmark, bookmark icon, disclosure in small text"},
    ],
}

PLANS = {"fcf087ea": FCF087EA, "fcf087ea-cf90-43cd-85fe-40bd96d58e3f": FCF087EA}


def write_md(plan: dict, path: Path):
    L = [f"# Creative Short Plan v2 — {plan['title']}",
         f"_content_id: {plan['content_id']} · platform: {plan['platform']} · target {plan['target_seconds']}s · privacy default: {plan['privacy_default']}_\n",
         f"- Voice tone: {plan['voice_tone']}",
         f"- Music mood: {plan['music_mood']} (use YouTube Audio Library — no copyright; or no music)",
         f"- Disclosure: {plan['disclosure']}\n",
         "## YouTube metadata",
         f"- Title: {plan['youtube']['title']}",
         f"- Hashtags: {' '.join('#'+h for h in plan['youtube']['hashtags'])}",
         "\n## Storyboard\n"]
    for s in plan["scenes"]:
        L.append(f"### Scene {s['id']} — {s['label']}\n"
                 f"- On-screen: **{s['onscreen']}**\n- Caption: {s['caption']}\n- VO: \"{s['vo']}\"\n"
                 f"- Visual: {s['visual']}\n- Motion: {s['motion']} · BG: {s['bg']}/{s['accent']}")
    L.append("\n## Manual fallback (Google Flow / CapCut)\n"
             "1. Use the VO lines per scene with Google AI Studio / a TTS for narration.\n"
             "2. Generate stickman/business scenes (Google Flow) per the Visual prompts.\n"
             "3. Add captions per scene; add YouTube Audio Library music (no copyright).\n"
             "4. Assemble in CapCut, 1080x1920, 30-45s; keep disclosure on the CTA scene.\n"
             "5. Export draft; do NOT upload until approved.")
    path.write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Author a creative short plan (md + scenes.json)")
    ap.add_argument("--content-id", default="fcf087ea")
    args = ap.parse_args()
    key = args.content_id
    plan = PLANS.get(key) or PLANS.get(key.split("-")[0])
    if not plan:
        print(f"! no built-in plan for {key}. Add one to PLANS."); return
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    stem = "fcf087ea_business_credit_myths_v2"
    md = PLAN_DIR / f"{stem}.md"
    js = PLAN_DIR / f"{stem}.scenes.json"
    write_md(plan, md)
    js.write_text(json.dumps(plan, indent=2))
    print(f"plan md:   {md}")
    print(f"scenes:    {js}")
    print(f"scenes: {len(plan['scenes'])} · target {plan['target_seconds']}s · voice {plan['voice']}")


if __name__ == "__main__":
    main()
