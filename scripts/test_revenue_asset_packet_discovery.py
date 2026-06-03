"""
test_revenue_asset_packet_discovery.py
Tests: assets are discovered from docs/reports/content, classified correctly.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_revenue_asset_packet_discovery ===\n")

from lib.hermes_revenue_asset_packet import (
    discover_revenue_assets, classify_revenue_asset, ASSET_CATEGORIES,
)
from pathlib import Path

# ── classify_revenue_asset ────────────────────────────────────────────────────
print("-- classify_revenue_asset filename classification --")
test_names = [
    ("credit_funding_readiness_checklist_draft_lead_magnet.md",   "lead_magnet"),
    ("credit_funding_readiness_checklist_draft_newsletter.md",    "newsletter"),
    ("credit_funding_readiness_checklist_draft_short_video_script.md", "short_video_script"),
    ("funding_readiness_yt_script.md",                            "youtube_script"),
    ("topic_seo_article.md",                                      "seo_article"),
    ("topic_linkedin.md",                                         "linkedin_post"),
    ("topic_x_posts.md",                                          "x_post"),
    ("checklist_draft_20260530.md",                               "checklist"),
    ("compliance_disclaimer_note.md",                             "compliance_note"),
]
for filename, expected_cat in test_names:
    p = Path(filename)
    got = classify_revenue_asset(p)
    check(f"classify('{filename[:55]}') == {expected_cat}", got == expected_cat)

# ── discover_revenue_assets finds files ───────────────────────────────────────
print("\n-- discover_revenue_assets --")
assets = discover_revenue_assets()
check("returns list", isinstance(assets, list))
check("at least 1 asset discovered", len(assets) >= 1)
check("all assets have path", all("path" in a for a in assets))
check("all assets have category", all("category" in a for a in assets))
check("all assets have filename", all("filename" in a for a in assets))
check("all assets have modified_at", all("modified_at" in a for a in assets))

# ── deduplication: one per category ──────────────────────────────────────────
print("\n-- deduplication: one per category --")
categories = [a["category"] for a in assets]
unique_cats = set(categories)
check("no duplicate categories", len(categories) == len(unique_cats))

# ── key asset types present ───────────────────────────────────────────────────
print("\n-- key revenue asset types present --")
cats_present = {a["category"] for a in assets}
check("checklist or lead_magnet found",
      "checklist" in cats_present or "lead_magnet" in cats_present)
check("newsletter or youtube_script found",
      "newsletter" in cats_present or "youtube_script" in cats_present
      or "short_video_script" in cats_present)

# ── categories are valid ──────────────────────────────────────────────────────
print("\n-- all categories are valid --")
for a in assets:
    check(f"category '{a['category']}' is valid", a["category"] in ASSET_CATEGORIES)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
