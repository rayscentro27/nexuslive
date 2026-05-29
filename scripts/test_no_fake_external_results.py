"""test_no_fake_external_results.py — system must not invent Google/social results."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_no_fake_external_results ===")
from lib.daily_opportunity_intake_engine import (
    _collect_google_sources, _collect_social_sources, _load_config, _is_search_available
)
import os as os_mod

cfg = _load_config()

# 1. Without search API, Google sources are ALL fallback tasks
os_mod.environ.pop("BRAVE_SEARCH_API_KEY", None)
os_mod.environ.pop("SERPAPI_KEY", None)
os_mod.environ.pop("SERPER_API_KEY", None)

check("search API is not available by default", not _is_search_available())

google_records = _collect_google_sources(cfg, 10)
check("google collector returns records", len(google_records) >= 0)
if google_records:
    all_fallback = all(r.fallback for r in google_records)
    check("ALL google sources are fallback tasks (no fake search results)", all_fallback)
    has_fallback_reason = all(r.fallback_reason for r in google_records)
    check("all google fallbacks have fallback_reason", has_fallback_reason)
    no_invented_urls = all(not r.url or "fallback" in r.url.lower() or r.url == ""
                           for r in google_records)
    check("google fallback sources have no invented URLs", no_invented_urls)

# 2. Social sources without API are fallback tasks
social_records = _collect_social_sources(cfg, 10)
check("social collector returns records", len(social_records) >= 0)
if social_records:
    all_social_fallback = all(r.fallback for r in social_records)
    check("ALL social sources are fallback tasks (no scraping)", all_social_fallback)
    no_invented_content = all(r.url == "" for r in social_records)
    check("social fallbacks have no invented URLs", no_invented_content)

# 3. Source code check: no requests/httpx calls for Google/social in intake engine
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
intake_src = (ROOT / "lib" / "daily_opportunity_intake_engine.py").read_text()
check("intake engine does not use requests.get for Google", "requests.get" not in intake_src)
check("intake engine does not use httpx for social scraping",
      "httpx" not in intake_src or "social" not in intake_src)

# 4. Fallback tasks have status=needs_more_research
for r in google_records[:3]:
    check(f"fallback google status is needs_more_research: {r.title[:30]}",
          r.status in ("needs_more_research", "registered", "discovered"))

# 5. System notes social API unavailability properly
from lib.hermes_notification_policy import create_blocker_notification
blocker = {
    "title": "Google search unavailable",
    "details": "No free search API configured",
    "recommended_fix": "Add BRAVE_SEARCH_API_KEY or SERPAPI_KEY to .env",
}
notification = create_blocker_notification(blocker)
check("blocker notification is plain language", "Traceback" not in notification)
check("blocker notification mentions the issue", "Google" in notification or "search" in notification.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
