#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a stronger Nexus rewrite prompt for weak social copy.")
    ap.add_argument("--text")
    ap.add_argument("--file")
    args = ap.parse_args()
    text = Path(args.file).read_text(errors="ignore") if args.file else (args.text or "")
    print(
        "Rewrite this Nexus copy to be more specific, emotionally compelling, and compliance-safe. "
        "Preserve the $97 Credit/Funding Readiness Starter Review, the monthly subscription path, "
        "and the Nexus Credit + Funding + Opportunity positioning. Improve the hook, pain point, "
        "specificity, CTA, and platform fit. Do not promise guaranteed funding, approval, deletions, "
        "score increases, or credit card approvals.\n\nCOPY:\n" + text.strip()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
