#!/usr/bin/env python3
"""
Review a showroom asset (CLI feedback fallback).

Ray approves / requests revisions on a reviewable asset. Writes feedback +
a Hermes learning-memory record so the NEXT content/trading loop can read
recent feedback before generating. Local only — no publish, no email, no
external send, no secrets.

Examples:
  python3 scripts/review_showroom_asset.py --asset-id asset_1234 --status revise \
      --feedback "Improve the hook and CTA"
  python3 scripts/review_showroom_asset.py --asset-id asset_1234 --status approved_with_notes \
      --feedback "Good direction. Next version needs stronger proof."
  python3 scripts/review_showroom_asset.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import showroom_assets as SA  # noqa: E402

FEEDBACK_JSON = ROOT / "logs" / "content_feedback_latest.json"
FEEDBACK_MD = ROOT / "logs" / "content_feedback_latest.md"
FEEDBACK_DIR = ROOT / "outputs" / "showroom" / "feedback"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _categorize(feedback: str) -> str:
    f = feedback.lower()
    for kw, cat in [("hook", "hook"), ("cta", "cta"), ("proof", "proof/credibility"),
                    ("title", "title"), ("length", "pacing/length"), ("tone", "tone"),
                    ("clarity", "clarity"), ("risk", "risk"), ("entry", "entry-logic"),
                    ("stop", "risk-management"), ("structure", "structure")]:
        if kw in f:
            return cat
    return "general"


def _lesson(asset_type: str, feedback: str, category: str) -> dict:
    return {
        "feedback": feedback,
        "category": category,
        "lesson_learned": f"For {asset_type}: address '{category}' — {feedback}",
        "next_prompt_adjustment": f"When generating {asset_type}, pre-check '{category}': {feedback}",
        "reusable_rule": f"{asset_type}:{category} -> {feedback[:80]}",
        "applied_to_future_content": "yes",
    }


def append_feedback_memory(rec: dict, status: str, feedback: str) -> dict:
    category = _categorize(feedback or "")
    lesson = _lesson(rec["asset_type"], feedback or "(approval, no notes)", category)
    entry = {
        "at": _now(), "asset_id": rec["asset_id"], "asset_type": rec["asset_type"],
        "title": rec.get("title"), "status": status, **lesson,
    }
    # JSON store (list)
    data = {"updated_at": _now(), "items": []}
    if FEEDBACK_JSON.exists():
        try:
            data = json.loads(FEEDBACK_JSON.read_text())
        except Exception:
            pass
    data["items"] = (data.get("items", []) + [entry])[-500:]
    data["updated_at"] = _now()
    FEEDBACK_JSON.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_JSON.write_text(json.dumps(data, indent=2))
    # MD store (human-readable, newest first)
    lines = ["# Content / Asset Feedback (learning memory)\n",
             f"_Updated: {_now()} · {len(data['items'])} feedback items_\n"]
    for it in reversed(data["items"][-40:]):
        lines.append(f"- **{it['asset_id']}** ({it['asset_type']}) → `{it['status']}` · {it['category']}: "
                     f"{it.get('feedback','')[:120]}")
    FEEDBACK_MD.write_text("\n".join(lines) + "\n")
    # per-asset copy
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    (FEEDBACK_DIR / f"{rec['asset_id']}_feedback.md").write_text(
        f"# Feedback — {rec['asset_id']} ({rec['asset_type']})\n\n"
        f"- title: {rec.get('title')}\n- status: {status}\n- category: {category}\n"
        f"- feedback: {feedback}\n- lesson: {lesson['lesson_learned']}\n"
        f"- next prompt adjustment: {lesson['next_prompt_adjustment']}\n- at: {_now()}\n")
    return lesson


def main() -> int:
    ap = argparse.ArgumentParser(description="Review a showroom asset (local feedback + learning memory).")
    ap.add_argument("--asset-id")
    ap.add_argument("--status", choices=SA.STATUSES)
    ap.add_argument("--feedback", default="")
    ap.add_argument("--list", action="store_true", help="list reviewable assets")
    args = ap.parse_args()

    if args.list or not args.asset_id:
        assets = SA.recent(50)
        if not assets:
            print("No reviewable assets yet. Run the content/trading loops + build_results_showroom.py.")
            return 0
        print(f"{'ASSET_ID':16} {'STATUS':30} {'TYPE':22} TITLE")
        for a in assets:
            print(f"{a['asset_id']:16} {a['status']:30} {a['asset_type']:22} {a['title'][:50]}")
        if not args.asset_id:
            return 0

    if not args.status:
        ap.error("--status is required when --asset-id is given")

    rec = SA.set_status(args.asset_id, args.status, feedback=args.feedback or None)
    if rec is None:
        print(f"Asset not found: {args.asset_id}. Use --list to see assets.")
        return 1
    lesson = append_feedback_memory(rec, args.status, args.feedback)
    SA.set_status(args.asset_id, args.status, lesson_memory="recorded")
    print(f"✓ {args.asset_id} → {args.status}")
    if args.feedback:
        print(f"  feedback: {args.feedback}")
        print(f"  lesson recorded → {FEEDBACK_JSON.relative_to(ROOT)} (category: {lesson['category']})")
    print("  future content/trading loops should read logs/content_feedback_latest.json before generating.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
