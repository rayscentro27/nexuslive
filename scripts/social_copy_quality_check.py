#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BANNED_PATTERNS = [
    r"(?<!no )(?<!not )(?<!without )\bguaranteed funding\b",
    r"(?<!no )(?<!not )(?<!without )\bguaranteed approvals?\b",
    r"(?<!no )(?<!not )(?<!without )\bguaranteed deletions?\b",
    r"(?<!no )(?<!not )(?<!without )\bguaranteed score increase\b",
    r"(?<!no )(?<!not )(?<!without )\bguaranteed credit repair\b",
    r"(?<!no )(?<!not )(?<!without )\bguaranteed credit card approvals?\b",
    r"\bdefinitely qualify\b",
    r"\bwill be removed\b",
    r"\bwill not show on your personal credit report\b",
    r"\bguaranteed \$?\d+[kKmM]?\b",
]
CTA_TERMS = ("comment ready", "dm ready", "checklist", "$97", "starter review", "newsletter", "join", "start with")
ALIGNMENT_TERMS = ("credit", "funding", "readiness", "business", "bankability", "nexus", "starter review", "subscription")
GENERIC_TERMS = ("get started today", "level up", "unlock your potential", "take your business to the next level")


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(term in low for term in terms)


def _score_hook(text: str) -> tuple[int, list[str]]:
    first = next((line.strip() for line in text.splitlines() if line.strip()), text.strip()[:140])
    score = 8
    reasons = []
    if len(first) <= 140:
        score += 3
    if re.search(r"\b(worst|denied|before|mistake|invisible|funding-ready|holding you back|why)\b", first, re.I):
        score += 6
    if "?" in first or re.search(r"\b(if|before|most|your)\b", first, re.I):
        score += 3
    if score < 14:
        reasons.append("Hook needs a sharper first-line tension or business-specific pain.")
    return min(score, 20), reasons


def evaluate(text: str) -> dict:
    low = text.lower()
    banned = [p for p in BANNED_PATTERNS if re.search(p, low, re.I)]
    reasons: list[str] = []
    suggestions: list[str] = []
    hook, hook_reasons = _score_hook(text)
    reasons.extend(hook_reasons)

    pain = 5 + min(10, sum(3 for w in ("denied", "cash", "funding", "credit", "lender", "documentation", "holding you back", "gap") if w in low))
    specificity = 5 + min(10, sum(2 for w in ("llc", "ein", "business phone", "address", "website", "domain email", "naics", "bank statements", "tier 1", "0%") if w in low))
    offer = 5 + min(10, sum(3 for w in ("$97", "starter review", "nexus", "monthly", "subscription", "credit/funding") if w in low))
    cta = 15 if _contains_any(text, CTA_TERMS) else 0
    compliance = 20

    if banned:
        compliance = 0
        reasons.append("Banned compliance claim detected.")
    if cta == 0:
        reasons.append("No clear CTA found.")
        suggestions.append("Add Comment READY, DM READY, checklist, newsletter, or $97 Starter Review CTA.")
    if not _contains_any(text, ALIGNMENT_TERMS):
        reasons.append("No clear credit/funding/business readiness alignment.")
    if _contains_any(text, GENERIC_TERMS) and specificity < 10:
        reasons.append("Copy reads too generic.")
        suggestions.append("Add concrete readiness factors like EIN, business address, domain email, documentation, or funding goal.")
    if offer < 10:
        suggestions.append("Tie the copy more clearly to the $97 review and monthly Nexus support path.")
    if pain < 10:
        suggestions.append("Name the reader's pain more directly.")
    if specificity < 10:
        suggestions.append("Add specific bankability or credit-readiness details.")

    total = hook + min(pain, 15) + min(specificity, 15) + min(offer, 15) + cta + compliance
    auto_fail = bool(banned) or cta == 0 or not _contains_any(text, ALIGNMENT_TERMS) or ("too generic" in " ".join(reasons).lower())
    passed = total >= 75 and not auto_fail
    return {
        "score": total,
        "pass": passed,
        "threshold": 75,
        "scores": {
            "hook_strength": hook,
            "pain_clarity": min(pain, 15),
            "specificity": min(specificity, 15),
            "offer_alignment": min(offer, 15),
            "cta_strength": cta,
            "compliance_safety": compliance,
        },
        "reasons": reasons,
        "suggestions": suggestions,
        "banned_claims_found": banned,
        "compliance_pass": not banned,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Score Nexus social copy quality and compliance.")
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.file:
        text = Path(args.file).read_text(errors="ignore")
    elif args.text:
        text = args.text
    else:
        raise SystemExit("--text or --file required")
    result = evaluate(text)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"score={result['score']} pass={result['pass']}")
        for reason in result["reasons"]:
            print(f"- {reason}")
        for suggestion in result["suggestions"]:
            print(f"* {suggestion}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
