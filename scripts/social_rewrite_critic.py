#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.social_copy_quality_check import evaluate  # noqa: E402


def recommendation(text: str) -> dict:
    result = evaluate(text)
    return {
        "score": result["score"],
        "pass": result["pass"],
        "rewrite_focus": result["suggestions"] or ["Make hook and CTA sharper while preserving compliance."],
        "recommended_structure": [
            "Start with a business/funding pain hook.",
            "Name a concrete readiness gap.",
            "Give one useful insight.",
            "Position Nexus as the diagnostic and monthly operating support.",
            "End with READY/checklist/$97 CTA and no-guarantee language.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Critique Nexus social copy and recommend rewrite focus.")
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    text = Path(args.file).read_text(errors="ignore") if args.file else (args.text or "")
    out = recommendation(text)
    print(json.dumps(out, indent=2) if args.json else "\n".join(out["rewrite_focus"]))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
