"""test_daily_opportunity_intake_engine.py"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_daily_opportunity_intake_engine ===")

from lib.daily_opportunity_intake_engine import (
    run_intake, IntakeRecord, _load_config, _collect_youtube_sources,
    _collect_google_sources, _collect_github_sources, _collect_monetization_sources,
)

# 1. Config loads
cfg = _load_config()
check("config loads", isinstance(cfg, dict))
check("config has youtube_keywords", bool(cfg.get("youtube_keywords")))
check("config has google_keywords", bool(cfg.get("google_keywords")))
check("config has github_keywords", bool(cfg.get("github_keywords")))

# 2. Source collectors return lists
yt = _collect_youtube_sources(cfg, 10)
check("youtube collector returns list", isinstance(yt, list))
check("youtube sources have intake_id", all(r.intake_id for r in yt))
check("youtube sources have source_type=youtube", all(r.source_type == "youtube" for r in yt))

goog = _collect_google_sources(cfg, 5)
check("google collector returns list", isinstance(goog, list))
check("google sources have intake_id", all(r.intake_id for r in goog))
# If no search API: all should be fallback tasks (NOT fake results)
if goog:
    search_available = bool(os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("SERPAPI_KEY"))
    if not search_available:
        check("google fallback tasks created (no fake results)", all(r.fallback for r in goog))
        check("google fallback has fallback_reason", all(r.fallback_reason for r in goog))

gh = _collect_github_sources(cfg, 5)
check("github collector returns list", isinstance(gh, list))
check("github sources have source_type=github", all(r.source_type == "github" for r in gh))

mon = _collect_monetization_sources(cfg, 10)
check("monetization collector returns list", isinstance(mon, list))
check("monetization sources have intake_id", all(r.intake_id for r in mon))

# 3. run_intake validation
result = run_intake(mode="validation", max_sources=15, register_artifacts=True, dry_run=True)
check("run_intake returns dict", isinstance(result, dict))
check("has records", isinstance(result.get("records"), list))
check("has stats", isinstance(result.get("stats"), dict))
check("has artifact_path", bool(result.get("artifact_path")))
check("has md_path", bool(result.get("md_path")))
check("stats.total > 0", result["stats"]["total"] > 0)
check("stats.total <= max_sources", result["stats"]["total"] <= 15)

# Artifact files exist
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
check("intake JSON artifact exists on disk", (ROOT / result["artifact_path"]).exists())
check("intake MD artifact exists on disk", (ROOT / result["md_path"]).exists())

# 4. Records have required fields
for r in result["records"][:3]:
    check(f"record has intake_id", bool(r.get("intake_id")))
    check(f"record has source_type", bool(r.get("source_type")))
    check(f"record has discovered_by", bool(r.get("discovered_by")))
    check(f"record has next_action", bool(r.get("next_action")))

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
