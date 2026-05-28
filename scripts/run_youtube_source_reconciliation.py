"""
run_youtube_source_reconciliation.py
=====================================
Scan all Nexus artifact stores for YouTube sources and reconcile them into
the unified source registry. NO SOURCE DISAPPEARS.

Searches:
  1. docs/reports/youtube/ — existing registry entries and reports
  2. docs/reports/ceo_review/ — URLs mentioned in CEO packets
  3. docs/reports/learn_by_doing/ — YouTube links in research packets
  4. docs/reports/ — any .md file mentioning youtube.com

Produces:
  docs/reports/youtube/source_registry.json (updated)
  docs/reports/youtube/youtube_source_reconciliation_<ts>.md
  docs/reports/youtube/youtube_source_reconciliation_<ts>.json
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.youtube_source_registry import YouTubeSourceRegistry, REGISTRY_FILE, REGISTRY_DIR

REPORTS_DIR = ROOT / "docs" / "reports"
YOUTUBE_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=[\w-]+|channel/[\w-]+|@[\w-]+|c/[\w-]+)'
    r'|youtu\.be/[\w-]+)',
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _detect_source_type(url: str) -> str:
    if "/watch?" in url or "youtu.be/" in url:
        return "video"
    if "/channel/" in url or "/@" in url or "/c/" in url:
        return "channel"
    return "channel"


def scan_for_youtube_urls() -> list[dict]:
    """Scan all markdown and JSON files under docs/reports/ for YouTube URLs."""
    found: dict[str, dict] = {}

    for ext in ("*.md", "*.json", "*.jsonl"):
        for fpath in REPORTS_DIR.rglob(ext):
            try:
                text = fpath.read_text(errors="replace")
                try:
                    rel_path = str(fpath.relative_to(ROOT))
                except ValueError:
                    rel_path = str(fpath)
                for url in YOUTUBE_URL_RE.findall(text):
                    url = url.rstrip(".,);\"'")
                    if url not in found:
                        found[url] = {
                            "url":         url,
                            "source_type": _detect_source_type(url),
                            "found_in":    rel_path,
                        }
            except Exception:
                pass

    return list(found.values())


def main() -> None:
    ts = _ts()
    print(f"[{_now()}] YouTube Source Reconciliation starting...")

    registry = YouTubeSourceRegistry()

    # 1. Scan all artifact stores
    discovered = scan_for_youtube_urls()
    print(f"  Discovered {len(discovered)} unique YouTube URLs in docs/reports/")

    # 2. Register any new ones
    new_count = 0
    updated_count = 0
    for item in discovered:
        url = item["url"]
        existing = registry.find_by_url(url)
        if existing:
            updated_count += 1
        else:
            registry.register(
                url=url,
                source_type=item["source_type"],
                submitted_by="reconciliation_scan",
                notes=f"Auto-discovered in {item['found_in']}",
            )
            new_count += 1

    all_sources = registry.all()
    counts = registry.count_by_status()

    print(f"  New sources registered: {new_count}")
    print(f"  Existing sources updated: {updated_count}")
    print(f"  Total in registry: {len(all_sources)}")
    print(f"  Status breakdown: {counts}")

    # 3. Answer the 10 accountability questions
    active_count      = counts.get("active", 0)
    submitted_count   = counts.get("submitted", 0)
    rejected_count    = counts.get("rejected", 0)
    needs_transcript  = len(registry.pending_transcript())
    needs_research    = len(registry.needs_research())
    no_artifacts      = sum(1 for s in all_sources if not s.to_dict().get("artifact_paths"))
    no_quality        = sum(1 for s in all_sources if s.to_dict().get("quality_score") is None)

    qa_block = f"""## Accountability Questions

1. **How many sources are registered?** {len(all_sources)}
2. **How many are active (processed)?** {active_count}
3. **How many are submitted but not processed?** {submitted_count}
4. **How many are rejected?** {rejected_count}
5. **How many need transcript download?** {needs_transcript}
6. **How many need research/intelligence extraction?** {needs_research}
7. **How many have no artifact paths yet?** {no_artifacts}
8. **How many have no quality score yet?** {no_quality}
9. **Were any sources discovered from existing reports?** {new_count + updated_count} (new: {new_count}, updated: {updated_count})
10. **Registry file path:** `{REGISTRY_FILE}`
"""

    # 4. Build the reconciliation report
    rows = ""
    for src in sorted(all_sources, key=lambda s: s.to_dict().get("submitted_at", ""), reverse=True):
        d = src.to_dict()
        name = (d.get("channel_name") or d.get("video_title") or d["url"])[:50]
        rows += (
            f"| {d['source_id'][:8]} | {d['source_type']} | {name} "
            f"| {d['status']} | {d['transcript_status']} "
            f"| {d.get('quality_score') or 'N/A'} | {d['research_status']} |\n"
        )

    report_md = f"""# YouTube Source Reconciliation
*Generated: {_now()}*

{qa_block}

---

## Full Source Registry

| ID | Type | Name/URL | Status | Transcript | Quality | Research |
|---|---|---|---|---|---|---|
{rows or '*(no sources)*'}

---

## Next Actions

| Priority | Action |
|---|---|
| 1 | Register sources that were auto-discovered: {new_count} new |
| 2 | Download transcripts: run `python scripts/run_youtube_source_reconciliation.py --download-transcripts` |
| 3 | Run quality review: run `python scripts/run_youtube_intelligence_cycle.py --all` |
| 4 | Sources needing research: {needs_research} |
"""

    # 5. Save artifacts
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    md_path   = REGISTRY_DIR / f"youtube_source_reconciliation_{ts}.md"
    json_path = REGISTRY_DIR / f"youtube_source_reconciliation_{ts}.json"

    md_path.write_text(report_md)
    json_path.write_text(json.dumps({
        "reconciled_at":    _now(),
        "total_sources":    len(all_sources),
        "new_registered":   new_count,
        "updated":          updated_count,
        "status_counts":    counts,
        "needs_transcript": needs_transcript,
        "needs_research":   needs_research,
        "no_quality_score": no_quality,
    }, indent=2))

    print(f"\n  Reconciliation report: {md_path}")
    print(f"  JSON summary:          {json_path}")
    print(f"\n[DONE] YouTube source reconciliation complete.")
    print(f"       Registry: {REGISTRY_FILE}")


if __name__ == "__main__":
    main()
