"""test_daily_digest_recommendation_only.py — digest sends recommendations, not spam."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_daily_digest_recommendation_only ===")
from lib.hermes_daily_monetization_digest import build_digest
from lib.hermes_notification_policy import create_digest_notification, NOTIFY_EACH_SOURCE

# Core anti-spam rules
check("digest_mode: NOTIFY_EACH_SOURCE is False", not NOTIFY_EACH_SOURCE)

# Build a typical digest and verify it's one message with recommendations
intake_results = {
    "stats": {"total": 25, "youtube": 10, "google": 6, "github": 4,
               "social": 3, "monetization": 2, "fallbacks": 8, "real_sources": 17},
    "records": [],
    "artifact_path": "docs/reports/intake/test.json",
    "md_path": "docs/reports/intake/test.md",
}
decision_results = {
    "top_opportunities": [
        {"title": "Credit repair affiliate program research", "status": "affiliate_candidate",
         "monetization_score": 80, "recommended_action": "Research affiliate terms",
         "requires_ray_approval": True, "approval_reason": "Affiliate signup", "why_selected": "High revenue",
         "goal_supported": "30-day revenue goal", "autonomous_next_step": ""},
        {"title": "Business funding checklist lead magnet", "status": "product_candidate",
         "monetization_score": 76, "recommended_action": "Draft checklist artifact",
         "requires_ray_approval": False, "why_selected": "Strong demand",
         "goal_supported": "Revenue goal", "autonomous_next_step": "Draft template"},
        {"title": "AI content faceless YouTube strategy", "status": "content_candidate",
         "monetization_score": 71, "recommended_action": "Create content brief",
         "requires_ray_approval": False, "why_selected": "Content engine",
         "goal_supported": "Content goal", "autonomous_next_step": "Build brief"},
    ],
    "rejected": [
        {"title": f"Low quality source {i}", "status": "reject", "why_rejected": "Low score",
         "monetization_score": i * 5} for i in range(8)
    ],
    "needs_approval": [{"title": "Affiliate signup", "approval_reason": "may require paid account"}],
    "top_recommendation": "Build a credit/funding readiness checklist as lead magnet",
    "blockers": [],
    "artifact_path": "docs/reports/monetization/test.json",
    "md_path": "docs/reports/monetization/test.md",
    "top_actions_path": "docs/reports/monetization/test_top.md",
    "rejected_path": "docs/reports/monetization/test_rejected.json",
}

digest = build_digest(intake_results, decision_results)
msg = digest["telegram_message"]

# The digest should be ONE message covering the whole cycle
check("digest is a single string", isinstance(msg, str))
check("digest summarizes total sources processed", "25" in msg or "sources" in msg.lower())
check("digest has top recommendation", "checklist" in msg.lower() or "credit" in msg.lower() or "lead magnet" in msg.lower())
check("digest does NOT mention each of 8 rejected sources individually",
      msg.count("Low quality source") < 3)  # should batch them, not list all 8
check("digest has reply options", "show" in msg.lower() or "reply" in msg.lower())
check("digest is under 4000 chars (Telegram limit)", len(msg) < 4000)
check("digest has no raw stack traces", "Traceback" not in msg)
check("digest has no raw JSON blobs", msg.count('{"') < 3)
check("digest mentions approval needed", "approval" in msg.lower() or "⏳" in msg)

# Verify cycle produces exactly ONE telegram message (not one per source)
# The create_digest_notification function returns one string
cycle_results = {
    "total_sources": 25,
    "useful_sources": 3,
    "rejected_sources": 8,
    "top_recommendation": "Build lead magnet",
    "top_opportunities": decision_results["top_opportunities"],
    "needs_approval": decision_results["needs_approval"],
    "blockers": [],
    "intake_artifact_path": "",
}
one_message = create_digest_notification(cycle_results)
check("create_digest_notification returns single string", isinstance(one_message, str))
check("single digest covers all 25 sources in one message", "25" in one_message or "sources" in one_message.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
