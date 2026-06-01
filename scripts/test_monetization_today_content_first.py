"""
test_monetization_today_content_first.py
Verifies that hermes_monetization_today.py produces content-first responses
using real local artifact data.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_monetization_today_content_first ===\n")

from lib.hermes_monetization_today import (
    find_current_content_assets,
    score_content_asset_for_monetization,
    build_today_monetization_plan,
    format_today_monetization_response,
    format_nexus_monetization_audit_response,
    is_monetization_audit_phrase,
    is_monetization_today_phrase,
)

# ── find_current_content_assets ─────────────────────────────────────────────
print("-- find_current_content_assets --")
assets = find_current_content_assets()
check("returns a list", isinstance(assets, list))
check("at least one asset found", len(assets) > 0)
if assets:
    a = assets[0]
    check("asset has path", "path" in a and bool(a["path"]))
    check("asset has asset_type", "asset_type" in a)
    check("asset has score (int)", "score" in a and isinstance(a["score"], int))
    check("asset score in range 0–100", 0 <= a["score"] <= 100)

# ── build_today_monetization_plan ─────────────────────────────────────────────
print("\n-- build_today_monetization_plan --")
plan = build_today_monetization_plan()
check("plan is dict", isinstance(plan, dict))
check("plan has assets key", "assets" in plan)
check("plan has asset_count", "asset_count" in plan and isinstance(plan["asset_count"], int))
check("plan has has_lead_magnet", "has_lead_magnet" in plan)
check("plan has has_newsletter", "has_newsletter" in plan)
check("asset_count matches len(assets)", plan["asset_count"] == len(find_current_content_assets()))

# ── format_today_monetization_response ────────────────────────────────────────
print("\n-- format_today_monetization_response --")
resp = format_today_monetization_response(plan)
check("response is non-empty string", bool(resp))
check("response has TODAY'S MONEY PLAN header", "TODAY'S MONEY PLAN" in resp)
check("no stale exec memory header", "**Monetization Priorities**" not in resp)
check("no 'Run nexus monetization audit' only line", resp.strip() != "Run `nexus monetization audit`")
check("has approval boundary note", "approval" in resp.lower())
check("no 'I can answer from verified artifacts'", "I can answer from verified artifacts" not in resp)
check("no 'Monetization evidence:'", "Monetization evidence:" not in resp)
check("no '[artifact_inventory]'", "[artifact_inventory]" not in resp)
check("no '[revenue_plan]'", "[revenue_plan]" not in resp)

# ── format_nexus_monetization_audit_response ──────────────────────────────────
print("\n-- format_nexus_monetization_audit_response --")
audit = format_nexus_monetization_audit_response(plan)
check("audit response is non-empty string", bool(audit))
check("audit has NEXUS MONETIZATION AUDIT header", "NEXUS MONETIZATION AUDIT" in audit)
check("audit has asset count", str(plan["asset_count"]) in audit or plan["asset_count"] == 0)
check("no generic evidence dump", "I can answer from verified artifacts" not in audit)
check("no 'Monetization evidence:'", "Monetization evidence:" not in audit)
check("has approval boundary note", "approval" in audit.lower())

# ── phrase classifiers ────────────────────────────────────────────────────────
print("\n-- phrase classifiers --")
check("'nexus monetization audit' is audit phrase", is_monetization_audit_phrase("nexus monetization audit"))
check("'run nexus monetization audit' is audit phrase", is_monetization_audit_phrase("run nexus monetization audit"))
check("'show monetization audit' is audit phrase", is_monetization_audit_phrase("show monetization audit"))
check("'how do we make money today' is not audit phrase", not is_monetization_audit_phrase("how do we make money today"))
check("'how do we make money today' is today phrase", is_monetization_today_phrase("how do we make money today"))
check("'monetization priorities' is today phrase", is_monetization_today_phrase("monetization priorities"))
check("'show source intake' is not monetization phrase", not is_monetization_today_phrase("show source intake"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
