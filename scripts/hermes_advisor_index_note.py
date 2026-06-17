#!/usr/bin/env python3
"""
Add a note to the Hermes Advisor knowledge base (knowledge/hermes_advisor/).

Usage:
  python3 scripts/hermes_advisor_index_note.py --title "T" --category research \
      --source "https://..." --body "summary text"

Categories map to subfolders: ray_profile, nexus_status, offers, research,
youtube_transcripts, business_strategy, decisions, meeting_notes, tools, handoffs,
archived_context. Safe/local only — no secrets, no network.
"""
from __future__ import annotations
import argparse, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "knowledge" / "hermes_advisor"
CATEGORIES = ("ray_profile", "nexus_status", "offers", "research", "youtube_transcripts",
              "business_strategy", "decisions", "meeting_notes", "tools", "handoffs", "archived_context")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--category", required=True, choices=CATEGORIES)
    ap.add_argument("--source", default="")
    ap.add_argument("--body", required=True)
    a = ap.parse_args()

    folder = KB / a.category
    folder.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "_", a.title.lower()).strip("_")[:60] or "note"
    fp = folder / f"{ts:%Y%m%d_%H%M%S}_{slug}.md"
    fp.write_text(
        f"---\ntitle: {a.title}\ncategory: {a.category}\nsource: {a.source}\n"
        f"created: {ts.isoformat()}\n---\n\n{a.body}\n"
    )
    print(f"indexed -> {fp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
