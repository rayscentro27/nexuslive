"""test_no_telegram_spam_from_daily_intake.py — intake must not spam Ray."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_no_telegram_spam_from_daily_intake ===")
from lib.hermes_notification_policy import should_notify_ray, batch_notifications, suppress_low_value_notifications

# Simulate 20 sources being registered
source_events = [{"event_type": "source_registered", "title": f"Source {i}"} for i in range(20)]
check("20 source_registered events → 0 notifications", not any(
    should_notify_ray(e["event_type"]) for e in source_events
))

# Simulate 8 sources being rejected
rejected_events = [{"event_type": "source_rejected"} for _ in range(8)]
check("8 source_rejected events → 0 notifications", not any(
    should_notify_ray(e["event_type"]) for e in rejected_events
))

# Simulate 5 scout assignments
scout_events = [{"event_type": "scout_assigned"} for _ in range(5)]
check("5 scout_assigned events → 0 notifications", not any(
    should_notify_ray(e["event_type"]) for e in scout_events
))

# Simulate 10 artifacts created
artifact_events = [{"event_type": "artifact_created"} for _ in range(10)]
check("10 artifact_created events → 0 notifications", not any(
    should_notify_ray(e["event_type"]) for e in artifact_events
))

# All 43 low-value events produce 0 Telegram messages
all_low_value = source_events + rejected_events + scout_events + artifact_events
filtered = suppress_low_value_notifications(all_low_value)
check("43 low-value events → 0 messages to Ray", len(filtered) == 0)

# Simulate a full cycle with one approval and one blocker
full_cycle_events = (
    source_events[:5]
    + rejected_events[:3]
    + scout_events[:2]
    + [{"event_type": "approval_required", "title": "Paid tool"}]
    + [{"event_type": "blocker", "title": "Search API down"}]
    + [{"event_type": "digest_ready"}]
)
batched = batch_notifications(full_cycle_events)
event_types_batched = {e["event_type"] for e in batched}
check("approval_required included in batched", "approval_required" in event_types_batched)
check("blocker included in batched", "blocker" in event_types_batched)
check("digest_ready included in batched", "digest_ready" in event_types_batched)
check("source_registered excluded from batched", "source_registered" not in event_types_batched)
check("source_rejected excluded from batched", "source_rejected" not in event_types_batched)
check("total batched messages <= 5 (not 16+)", len(batched) <= 5)

# Verify intake engine does not call Telegram for each source
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
intake_src = (ROOT / "lib" / "daily_opportunity_intake_engine.py").read_text()
check("intake engine does not send Telegram per source", "send_telegram" not in intake_src and "telegram_send" not in intake_src)
check("intake engine does not call bot.send_message in hot loop", "send_message" not in intake_src)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
