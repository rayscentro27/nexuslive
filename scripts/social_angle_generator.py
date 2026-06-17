#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

ANGLE_TYPES = [
    ("pain angle", "The day you need funding is the worst day to discover your business is not funding-ready."),
    ("opportunity angle", "A cleaner credit/funding profile can open better conversations before you apply."),
    ("checklist angle", "Before you chase funding, run the readiness checklist."),
    ("myth-busting angle", "An LLC alone does not make a business bankable."),
    ("story/problem angle", "A business owner gets denied and only then learns what lenders were really checking."),
    ("proof/result angle", "The first Nexus Facebook queue post proved the system can publish; now the copy needs to convert."),
    ("direct CTA angle", "Start with the $97 Credit/Funding Readiness Starter Review."),
    ("subscription angle", "The $97 review diagnoses the gap; monthly support helps execute the plan."),
    ("business opportunity angle", "Credit readiness plus opportunity research turns scattered ideas into a plan."),
    ("funding readiness angle", "Prepare the business foundation before Tier 1 funding applications."),
]


def build(topic: str, offer: str, platform: str) -> list[dict]:
    out = []
    for title, hook in ANGLE_TYPES:
        out.append({
            "angle_title": title,
            "hook": hook,
            "body_idea": f"Connect {topic} to one concrete readiness gap, then position Nexus as the practical review and support system.",
            "cta": "Comment READY for the checklist." if platform == "facebook" else "DM READY for the checklist.",
            "platform_recommendation": platform,
            "offer": offer,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Nexus creative social angles.")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--offer", default="Credit/Funding Readiness Starter Review - $97")
    ap.add_argument("--platform", default="facebook")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    angles = build(args.topic, args.offer, args.platform)
    print(json.dumps({"angles": angles}, indent=2) if args.json else "\n\n".join(f"{a['angle_title']}: {a['hook']}" for a in angles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
