#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import showroom_assets as SA  # noqa: E402

OUT = ROOT / "outputs" / "monetization" / "content_growth_pack"
STATUS = ROOT / "reports" / "showroom" / "content_growth_pack_status.md"


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def register(asset_type: str, title: str, path: Path) -> dict:
    rel = str(path.relative_to(ROOT))
    return SA.register(asset_type, title, rel, showroom_path=rel, key=rel)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    files: dict[str, Path] = {}

    files["offer_brief"] = OUT / "offer_brief.md"
    write(files["offer_brief"], f"""# 30-Day AI Content Growth Pack — Offer Brief

_Generated: {now}_

## Offer
30-Day AI Content Growth Pack

## Target Buyers
- Small business owners
- Coaches and consultants
- Funding / credit professionals
- Real estate professionals
- Local service businesses
- Small agencies

## Promise
Nexus helps the buyer leave the month with a consistent content system, a repeatable publishing queue, and reviewable assets they can improve over time.

## What They Get
- 30 days of content themes and content prompts
- Newsletter topics and short-form video ideas
- Social draft queue
- One HyperFrames-ready video packet
- Storyboard and thumbnail prompt
- Landing-page draft and lead magnet outline
- Review loop with revision notes

## Beta Pricing Options
- Option A: $197 beta
- Option B: $297 setup + $497/month after validation

## Important Boundaries
- No income guarantees
- No growth guarantees
- No promise of virality
- No publishing without approval
- Position as a done-with-you content operating pack, not a magic result engine

## Why This Fits Nexus
Nexus already creates reviewable drafts, short-form scripts, HyperFrames packets, storyboard prompts, and learning-memory notes. This product turns those internal lanes into a packaged service offer.
""")

    files["landing_page"] = OUT / "landing_page_draft.md"
    write(files["landing_page"], """# Landing Page Draft — 30-Day AI Content Growth Pack

## Hero
Turn scattered ideas into a 30-day content system your business can actually review, refine, and reuse.

### Subhead
Built for small businesses, consultants, funding/credit professionals, real estate pros, and local service brands that need steady marketing output without hiring a full content team.

## CTA
Apply for the beta review pack

## Problem
Most small businesses do not need more random content ideas. They need a repeatable system that turns ideas into assets, organizes revisions, and keeps future content improving.

## Solution
The 30-Day AI Content Growth Pack gives you a practical content operating system:
- offer and lead-magnet positioning
- newsletter and video topic planning
- social drafts
- reviewable video packet assets
- revision notes so the next batch improves

## Deliverables
- offer brief
- landing-page draft
- lead magnet outline
- 4 newsletter ideas
- 8 short video ideas
- 4 social drafts
- 1 HyperFrames-ready packet
- storyboard and thumbnail prompt

## Beta Pricing
- $197 beta
- or $297 setup + $497/month after validation

## Compliance / Trust
No guarantee of followers, leads, or sales. This is a content-system offer designed to improve clarity, consistency, and review velocity.

## CTA Close
If your business already has expertise but your content is inconsistent, this pack is the fastest way to get a month of reviewable marketing assets on the table.
""")

    files["lead_magnet"] = OUT / "lead_magnet_outline.md"
    write(files["lead_magnet"], """# Lead Magnet Outline

## Title
The 30-Day Content Operating Checklist for Small Businesses

## Sections
1. Why inconsistent content kills momentum
2. The five asset types a small business should reuse every month
3. How to turn one topic into newsletter, short video, and social variants
4. Review loop: what to fix instead of starting over
5. Simple weekly cadence for creating and revising
6. What should stay manual vs AI-assisted

## CTA
Book the 30-Day AI Content Growth Pack beta if you want this built for your business.
""")

    files["newsletter_ideas"] = OUT / "newsletter_topic_ideas.md"
    write(files["newsletter_ideas"], """# Newsletter Topic Ideas

1. Why most small businesses do content backward
2. The 30-day content system that reduces idea fatigue
3. How to reuse one expert idea across four channels
4. What to measure before you scale content volume
""")

    files["video_ideas"] = OUT / "short_video_ideas.md"
    write(files["video_ideas"], """# Short-Form Video Ideas

1. The real reason your business content feels random
2. Stop posting more. Start reusing better.
3. One topic. Four assets. One review loop.
4. The easiest way to plan 30 days of content
5. Why most service businesses never build a content system
6. The review-first content workflow that keeps improving
7. How consultants can turn client questions into content
8. What a monthly content pack should actually include
""")

    files["social_drafts"] = OUT / "social_post_drafts.md"
    write(files["social_drafts"], """# Social Post Drafts

## Draft 1
Most businesses do not need more content ideas. They need a repeatable system for turning expertise into reviewable assets they can improve over time.

## Draft 2
If your team keeps starting content from scratch, the real problem is not creativity. It is missing process.

## Draft 3
One strong topic can become a newsletter, a short video, a landing-page angle, and four social drafts. The bottleneck is usually review, not ideas.

## Draft 4
The 30-Day AI Content Growth Pack is designed for businesses that want consistent content without pretending AI alone will do strategy for them.
""")

    files["hyperframes_packet"] = OUT / "content_growth_pack_hyperframes_packet.md"
    write(files["hyperframes_packet"], """# HyperFrames Packet — 30-Day AI Content Growth Pack

- asset theme: content systems for small business
- title: Build 30 Days of Content Without Starting From Scratch
- hook: Most business content fails because the system is missing.
- voiceover:
  Stop chasing random content ideas. A 30-day content system gives your business a repeatable way to turn expertise into newsletters, short videos, social drafts, and landing-page angles. The goal is not perfection. The goal is visible assets, faster reviews, and better revisions every cycle.
- scene list:
  1. Hook: random ideas vs real system
  2. Problem: inconsistent posting and starting from scratch
  3. Solution: monthly pack with reusable assets
  4. CTA: review your first 30-day content pack
- visual prompts:
  - dashboard cards filling a monthly content board
  - simple workflow arrows from topic to asset types
  - revision notes improving a second version
  - final CTA card with clean compliance footer
- CTA:
  Review the 30-Day AI Content Growth Pack beta
- compliance notes:
  No growth guarantees. No revenue guarantees. Present as a workflow and production system.
""")

    files["storyboard"] = OUT / "content_growth_pack_storyboard.md"
    write(files["storyboard"], """# Storyboard

1. Calendar wall with empty content slots turning into filled cards
2. Split-screen: random posting on one side, structured asset pipeline on the other
3. Asset stack visual: newsletter, short video, social draft, landing page
4. Revision notes overlay showing how the second batch improves
5. Final CTA panel: 30-Day AI Content Growth Pack
""")

    files["thumbnail"] = OUT / "content_growth_pack_thumbnail_prompt.md"
    write(files["thumbnail"], """# Thumbnail Prompt

Create a high-contrast vertical thumbnail for a short video about a 30-day content system for small businesses. Use bold 3-5 word text such as "30 DAYS OF CONTENT" with a clean dashboard/calendar visual, bright accent color, and no income claims.
""")

    files["postiz_payload"] = OUT / "postiz_draft_payload.md"
    write(files["postiz_payload"], """# Postiz Draft Payload — Draft Only

- status: ready_to_publish_pending_approval
- publish action: blocked
- channel intent: LinkedIn / X / Facebook page draft later
- exact copy:
  Most small businesses do not need more random content ideas. They need a system that turns one good topic into newsletters, short videos, social drafts, and landing-page angles they can actually review and improve.
- rollback:
  Delete the draft payload file and leave Postiz disconnected until Ray approves exact scheduling.
""")

    files["compliance"] = OUT / "compliance_and_safety_notes.md"
    write(files["compliance"], """# Compliance / Safety Notes

- Do not promise leads, followers, revenue, or virality
- Do not claim this replaces strategy or human review
- Do not use client names or testimonials without approval
- Keep all drafts local and reviewable until Ray approves exact public use
- Keep payment and Stripe inactive until separate approval
""")

    files["review_checklist"] = OUT / "ray_review_checklist.md"
    write(files["review_checklist"], """# Ray Review Checklist

- Is the target buyer specific enough?
- Is the pricing positioned as beta/testing, not guaranteed ROI?
- Does the landing page sound practical instead of hypey?
- Do the social drafts feel useful and credible?
- Is the HyperFrames packet strong enough to become a real draft later?
- Should this pack focus first on funding/credit professionals before general SMBs?
""")

    assets = {
        "offer_brief": register("monetization_packet", "30-Day AI Content Growth Pack Offer Brief", files["offer_brief"]),
        "landing_page": register("landing_page_draft", "30-Day AI Content Growth Pack Landing Page", files["landing_page"]),
        "lead_magnet": register("lead_magnet", "30-Day AI Content Growth Pack Lead Magnet", files["lead_magnet"]),
        "newsletter_ideas": register("newsletter_ideas", "30-Day AI Content Growth Pack Newsletter Ideas", files["newsletter_ideas"]),
        "video_ideas": register("video_ideas", "30-Day AI Content Growth Pack Video Ideas", files["video_ideas"]),
        "social_drafts": register("social_draft", "30-Day AI Content Growth Pack Social Drafts", files["social_drafts"]),
        "hyperframes_packet": register("video_packet", "30-Day AI Content Growth Pack HyperFrames Packet", files["hyperframes_packet"]),
        "storyboard": register("storyboard", "30-Day AI Content Growth Pack Storyboard", files["storyboard"]),
        "thumbnail": register("thumbnail_prompt", "30-Day AI Content Growth Pack Thumbnail Prompt", files["thumbnail"]),
        "postiz_payload": register("postiz_draft", "30-Day AI Content Growth Pack Postiz Draft Payload", files["postiz_payload"]),
        "compliance": register("compliance_notes", "30-Day AI Content Growth Pack Compliance Notes", files["compliance"]),
        "review_checklist": register("review_checklist", "30-Day AI Content Growth Pack Ray Review Checklist", files["review_checklist"]),
    }

    status_lines = [
        "# 30-Day AI Content Growth Pack Status",
        f"_Generated: {now}_",
        "",
        "Nexus is not looking for finished opportunities; Nexus is looking for seeds it can improve, test, and evolve into monetizable systems.",
        "",
        "## Assets",
    ]
    for key, path in files.items():
        asset = assets.get(key)
        status_lines += [
            f"### {key.replace('_', ' ').title()}",
            f"- path: `{path.relative_to(ROOT)}`",
            f"- asset_id: `{asset['asset_id']}`" if asset else "- asset_id: n/a",
            f"- status: `{asset['status']}`" if asset else "- status: n/a",
            f"- review command: `{asset['review_command']}`" if asset else "- review command: n/a",
            f"- revise command: `{asset['feedback_command']}`" if asset else "- revise command: n/a",
            f"- approved_with_notes command: `python3 scripts/review_showroom_asset.py --asset-id {asset['asset_id']} --status approved_with_notes --feedback \"...\"`" if asset else "- approved_with_notes command: n/a",
            "",
        ]
    write(STATUS, "\n".join(status_lines) + "\n")
    print(STATUS.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
