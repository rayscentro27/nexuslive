"""test_hermes_notification_policy.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_hermes_notification_policy ===")
from lib.hermes_notification_policy import (
    should_notify_ray, suppress_low_value_notifications, batch_notifications,
    create_digest_notification, create_approval_notification, create_blocker_notification,
    notification_policy_summary,
    NOTIFY_EACH_SOURCE, NOTIFY_REJECTED_SOURCE, NOTIFY_SCOUT_ASSIGNMENT,
    NOTIFY_ARTIFACT_CREATED, NOTIFY_APPROVAL_REQUIRED, NOTIFY_BLOCKER, NOTIFY_HIGH_VALUE,
)

# Default settings
check("source_registered suppressed by default", not NOTIFY_EACH_SOURCE)
check("source_rejected suppressed by default", not NOTIFY_REJECTED_SOURCE)
check("scout_assigned suppressed by default", not NOTIFY_SCOUT_ASSIGNMENT)
check("artifact_created suppressed by default", not NOTIFY_ARTIFACT_CREATED)
check("approval_required notifies by default", NOTIFY_APPROVAL_REQUIRED)
check("blocker notifies by default", NOTIFY_BLOCKER)
check("high_value_opportunity notifies by default", NOTIFY_HIGH_VALUE)

# should_notify_ray
check("source_registered → no notify", not should_notify_ray("source_registered"))
check("source_rejected → no notify", not should_notify_ray("source_rejected"))
check("scout_assigned → no notify", not should_notify_ray("scout_assigned"))
check("artifact_created → no notify", not should_notify_ray("artifact_created"))
check("approval_required → notify", should_notify_ray("approval_required"))
check("blocker → notify", should_notify_ray("blocker"))
check("high_value_opportunity → notify", should_notify_ray("high_value_opportunity"))
check("digest_ready → notify", should_notify_ray("digest_ready"))
check("opportunity_scored with score 80 → notify",
      should_notify_ray("opportunity_scored", context={"monetization_score": 80}))
check("opportunity_scored with score 40 → no notify",
      not should_notify_ray("opportunity_scored", context={"monetization_score": 40}))

# suppress_low_value_notifications
events = [
    {"event_type": "source_registered"},
    {"event_type": "source_rejected"},
    {"event_type": "scout_assigned"},
    {"event_type": "approval_required"},
    {"event_type": "blocker"},
    {"event_type": "high_value_opportunity"},
]
filtered = suppress_low_value_notifications(events)
check("low-value events suppressed", len(filtered) < len(events))
event_types = {e["event_type"] for e in filtered}
check("approval_required passes filter", "approval_required" in event_types)
check("blocker passes filter", "blocker" in event_types)
check("source_registered filtered out", "source_registered" not in event_types)
check("source_rejected filtered out", "source_rejected" not in event_types)

# batch_notifications
batched = batch_notifications(events)
check("batch reduces event count", len(batched) <= len(events))

# create_digest_notification
cycle_results = {
    "total_sources": 20, "useful_sources": 5, "rejected_sources": 10,
    "top_recommendation": "Build a credit repair lead magnet",
    "top_opportunities": [
        {"title": "Credit repair checklist", "monetization_score": 82, "status": "product_candidate"},
    ],
    "needs_approval": [],
    "blockers": [],
    "intake_artifact_path": "docs/reports/intake/test.md",
}
digest_msg = create_digest_notification(cycle_results)
check("digest message non-empty", len(digest_msg) > 50)
check("digest no raw JSON", digest_msg.count("{") < 5)
check("digest has source count", "20" in digest_msg or "sources" in digest_msg.lower())
check("digest has recommendation", "credit" in digest_msg.lower() or "lead magnet" in digest_msg.lower())
check("digest is plain language", "Traceback" not in digest_msg)

# create_approval_notification
approval_msg = create_approval_notification({"title": "Stripe signup", "approval_reason": "payment activation"})
check("approval message mentions approval", "approval" in approval_msg.lower() or "approved" in approval_msg.lower() or "Approval" in approval_msg)
check("approval message mentions item", "Stripe" in approval_msg)

# create_blocker_notification
blocker_msg = create_blocker_notification({"title": "Search API unavailable", "recommended_fix": "Add API key"})
check("blocker message is non-empty", len(blocker_msg) > 10)
check("blocker message mentions blocker", "Blocker" in blocker_msg or "blocker" in blocker_msg.lower())

# notification_policy_summary
summary = notification_policy_summary()
check("policy summary is string", isinstance(summary, str))
check("policy summary mentions digest mode", "digest" in summary.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
