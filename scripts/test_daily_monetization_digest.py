"""test_daily_monetization_digest.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_daily_monetization_digest ===")
from lib.hermes_daily_monetization_digest import build_digest, digest_plain_english
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

# Build digest from sample data
intake_results = {
    "stats": {"total": 20, "youtube": 8, "google": 5, "github": 3, "social": 2, "monetization": 2,
               "fallbacks": 6, "real_sources": 14, "high_potential": 5},
    "records": [],
    "artifact_path": "docs/reports/intake/test_intake.json",
    "md_path": "docs/reports/intake/test_intake.md",
}
decision_results = {
    "top_opportunities": [
        {"title": "Credit repair checklist lead magnet", "status": "client_education_candidate",
         "monetization_score": 82, "recommended_action": "Draft checklist for Ray review",
         "requires_ray_approval": False, "why_selected": "High demand, aligns with 30-day goal",
         "goal_supported": "30-day revenue goal", "autonomous_next_step": "Draft checklist template"},
        {"title": "Affiliate program research: business funding", "status": "affiliate_candidate",
         "monetization_score": 74, "recommended_action": "Research affiliate terms",
         "requires_ray_approval": True, "approval_reason": "Affiliate signup may require paid account",
         "why_selected": "Strong revenue signal", "goal_supported": "Revenue goal"},
    ],
    "rejected": [{"title": "Cooking video", "status": "reject", "why_rejected": "Low score",
                   "monetization_score": 12}],
    "needs_approval": [{"title": "Affiliate program", "approval_reason": "signup may require paid account"}],
    "top_recommendation": "Draft a credit/funding readiness checklist as a lead magnet",
    "blockers": [],
    "artifact_path": "docs/reports/monetization/test_decision.json",
    "md_path": "docs/reports/monetization/test_decision.md",
    "top_actions_path": "docs/reports/monetization/test_top.md",
    "rejected_path": "docs/reports/monetization/test_rejected.json",
}

digest = build_digest(intake_results, decision_results)
check("build_digest returns dict", isinstance(digest, dict))
check("has telegram_message", bool(digest.get("telegram_message")))
check("has review_md_path", bool(digest.get("review_md_path")))
check("has review_json_path", bool(digest.get("review_json_path")))
check("has top_opportunities", isinstance(digest.get("top_opportunities"), list))

msg = digest["telegram_message"]
check("telegram message is non-empty", len(msg) > 50)
check("telegram message has no raw JSON dump", msg.count("{") < 10)
check("telegram message mentions sources", any(w in msg.lower() for w in ["sources", "reviewed"]))
check("telegram message mentions recommendation or best move",
      "best move" in msg.lower() or "recommend" in msg.lower() or "opportunit" in msg.lower())
check("telegram message in common language (no stack traces)", "Traceback" not in msg)
check("telegram message has reply options", "show" in msg.lower() or "reply" in msg.lower())
check("telegram message is concise (< 4000 chars)", len(msg) < 4000)

# Review artifact created
check("review MD artifact created", (ROOT / digest["review_md_path"]).exists() if not digest["review_md_path"].startswith("docs/reports/intake") else True)

# digest_plain_english
pe = digest_plain_english(limit_ops=5)
check("digest_plain_english returns string", isinstance(pe, str))
check("digest_plain_english is non-empty", len(pe) > 10)
check("digest_plain_english has no raw stack traces", "Traceback" not in pe)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
