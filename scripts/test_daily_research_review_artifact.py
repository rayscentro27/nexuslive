"""test_daily_research_review_artifact.py"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_daily_research_review_artifact ===")
from pathlib import Path
from lib.hermes_daily_monetization_digest import build_digest
ROOT = Path(__file__).resolve().parent.parent

intake_results = {
    "stats": {"total": 15, "youtube": 6, "google": 4, "github": 2,
               "social": 1, "monetization": 2, "fallbacks": 5, "real_sources": 10},
    "records": [],
    "artifact_path": "docs/reports/intake/test_intake.json",
    "md_path": "docs/reports/intake/test_intake.md",
}
decision_results = {
    "top_opportunities": [
        {"title": "Lead magnet: business funding readiness", "status": "product_candidate",
         "monetization_score": 78, "recommended_action": "Draft checklist",
         "requires_ray_approval": False, "why_selected": "High demand",
         "goal_supported": "30-day revenue goal", "autonomous_next_step": "Draft template"},
    ],
    "rejected": [{"title": "Low score source", "status": "reject", "why_rejected": "Low potential",
                   "monetization_score": 18}],
    "needs_approval": [],
    "top_recommendation": "Build a lead magnet checklist",
    "blockers": [],
    "artifact_path": "", "md_path": "", "top_actions_path": "", "rejected_path": "",
}

digest = build_digest(intake_results, decision_results)
review_md_path = ROOT / digest["review_md_path"]
review_json_path = ROOT / digest["review_json_path"]

check("review MD exists", review_md_path.exists())
check("review JSON exists", review_json_path.exists())

if review_md_path.exists():
    content = review_md_path.read_text()
    check("review mentions what was searched", "searched" in content.lower() or "nexus searched" in content.lower())
    check("review has sources collected section", "sources collected" in content.lower())
    check("review has what was useful section", "useful" in content.lower())
    check("review has rejected section", "rejected" in content.lower())
    check("review has what hermes recommends", "recommend" in content.lower())
    check("review has scouts section", "scout" in content.lower())
    check("review has actions section", "action" in content.lower())
    check("review has needs approval section", "approval" in content.lower())
    check("review has evidence paths", "evidence" in content.lower() or "artifact" in content.lower())
    check("review mentions scheduler not enabled", "scheduler" in content.lower())
    check("review is common language (no Traceback)", "Traceback" not in content)

if review_json_path.exists():
    data = json.loads(review_json_path.read_text())
    check("JSON has review_id", bool(data.get("review_id")))
    check("JSON has intake_stats", bool(data.get("intake_stats")))
    check("JSON has top_opportunities", isinstance(data.get("top_opportunities"), list))

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
