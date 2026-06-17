#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.social_copy_quality_check import evaluate  # noqa: E402


def facebook_draft(topic: str, offer: str, idx: int) -> str:
    hooks = [
        "The day you need funding is the worst day to learn your business is not funding-ready.",
        "Your business can look real to you and still look unfinished to lenders.",
        "Most funding denials start before the application is ever submitted.",
    ]
    hook = hooks[idx % len(hooks)]
    return (
        f"{hook}\n\n"
        f"If you are chasing {topic}, slow down long enough to check the basics: entity details, EIN, business phone, address, website, domain email, NAICS, bank statements, and credit-readiness gaps.\n\n"
        "Nexus starts with the $97 Credit/Funding Readiness Starter Review so you can see what may be holding you back before you apply. If the gaps are bigger, monthly Nexus Credit + Funding + Opportunity support helps you work the plan week by week.\n\n"
        "Comment READY for the checklist. Readiness and preparation only; no guaranteed funding, approvals, deletions, or score increases."
    )


def instagram_draft(topic: str, offer: str, idx: int) -> str:
    return (
        f"Before you apply for {topic}, check the business foundation.\n\n"
        "LLC. EIN. Business phone. Address. Website. Domain email. NAICS. Bank statements. Credit-readiness gaps.\n\n"
        "The $97 Nexus Starter Review helps map what may be holding you back, then monthly support helps you execute.\n\n"
        "DM READY for the checklist. No guaranteed funding or approval."
    )


def video_draft(topic: str, offer: str, idx: int) -> str:
    return (
        "3-second hook: Stop applying for funding before your business looks fundable.\n"
        f"Pain: Business owners get denied for {topic} because the profile is incomplete.\n"
        "Insight: Lenders may look at consistency, documentation, credit readiness, and bankability signals.\n"
        "Nexus angle: Start with the $97 Starter Review, then use monthly support to work the gaps.\n"
        "CTA: Comment READY for the checklist. No guaranteed approvals or funding."
    )


def landing_draft(topic: str, offer: str, idx: int) -> str:
    return (
        "Hero: Find the credit and funding-readiness gaps before you apply.\n"
        f"Problem: {topic} gets harder when your business profile, documents, and credit-readiness signals do not line up.\n"
        "Offer: The $97 Credit/Funding Readiness Starter Review gives you a practical gap map.\n"
        "Upgrade: Monthly Nexus support helps with credit readiness, business bankability, dispute workflow organization, funding prep, and opportunity execution.\n"
        "CTA: Start with the $97 review. No guaranteed funding, approvals, deletions, or score increases."
    )


def newsletter_draft(topic: str, offer: str, idx: int) -> str:
    return (
        f"Subject: Before you apply for {topic}, check these 7 signals\n\n"
        "This week: business funding readiness starts with consistency. Review your entity, EIN, phone, address, website, domain email, NAICS, bank statements, and credit-readiness gaps.\n\n"
        "Nexus path: checklist -> $97 Starter Review -> monthly Credit + Funding + Opportunity support.\n\n"
        "CTA: Reply READY for the checklist. No guaranteed approvals or funding."
    )


BUILDERS = {
    "facebook": facebook_draft,
    "instagram": instagram_draft,
    "video": video_draft,
    "landing": landing_draft,
    "newsletter": newsletter_draft,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Nexus draft content from a topic/source.")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--source-file")
    ap.add_argument("--platform", choices=sorted(BUILDERS), required=True)
    ap.add_argument("--offer", default="Credit/Funding Readiness Starter Review - $97")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    source_note = Path(args.source_file).read_text(errors="ignore")[:500] if args.source_file else ""
    items = []
    for i in range(args.count):
        text = BUILDERS[args.platform](args.topic, args.offer, i)
        if source_note:
            text += f"\n\nSource note: {source_note}"
        score = evaluate(text)
        items.append({
            "platform": args.platform,
            "topic": args.topic,
            "offer": args.offer,
            "text": text,
            "quality": score,
            "status": "ready" if score["pass"] else "needs_revision",
        })
    print(json.dumps({"items": items}, indent=2) if args.json else "\n\n---\n\n".join(i["text"] for i in items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
