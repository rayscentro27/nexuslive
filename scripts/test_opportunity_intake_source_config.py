"""test_opportunity_intake_source_config.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_opportunity_intake_source_config ===")
import yaml
ROOT = Path(__file__).resolve().parent.parent
cfg_path = ROOT / "config" / "opportunity_intake_sources.yaml"

check("config file exists", cfg_path.exists())
cfg = yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else {}
check("config is dict", isinstance(cfg, dict))

# Sections
check("has youtube_channels", bool(cfg.get("youtube_channels")))
check("has youtube_keywords", bool(cfg.get("youtube_keywords")))
check("has google_keywords", bool(cfg.get("google_keywords")))
check("has social_keywords", bool(cfg.get("social_keywords")))
check("has github_keywords", bool(cfg.get("github_keywords")))
check("has monetization_categories", bool(cfg.get("monetization_categories")))
check("has scoring_weights", bool(cfg.get("scoring_weights")))
check("has thresholds", bool(cfg.get("thresholds")))

# YouTube keywords cover key niches
yt_kws = cfg.get("youtube_keywords", {})
if isinstance(yt_kws, dict):
    all_kw = " ".join(kw for group in yt_kws.values() for kw in group).lower()
else:
    all_kw = " ".join(yt_kws).lower()
check("youtube keywords cover credit/funding", "credit" in all_kw or "fund" in all_kw)
check("youtube keywords cover AI/content", "ai" in all_kw or "content" in all_kw)
check("youtube keywords cover affiliate", "affiliate" in all_kw or "monetiz" in all_kw)

# Social platforms document API availability
social_platforms = cfg.get("social_platforms", [])
check("social platforms listed", len(social_platforms) >= 3)
check("social platforms note API unavailability",
      any("no api" in str(p.get("note","")).lower() for p in social_platforms if isinstance(p, dict)))

# Monetization categories
cats = cfg.get("monetization_categories", [])
check("at least 5 monetization categories", len(cats) >= 5)
check("affiliate in categories", "affiliate" in cats)
check("lead_magnet in categories", "lead_magnet" in cats)

# Thresholds
thresh = cfg.get("thresholds", {})
check("has reject_below_monetization_score", "reject_below_monetization_score" in thresh)
check("has high_value_above_monetization_score", "high_value_above_monetization_score" in thresh)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
