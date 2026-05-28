"""Test HermesProactiveNotifier — compose messages without actually sending."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from lib.hermes_proactive_notifier import HermesProactiveNotifier, NOTIFY_LOG

def main():
    notifier = HermesProactiveNotifier()

    # These will attempt to send via hermes_gate but gate will suppress (no bot token in test env)
    sent = notifier.notify_cycle_complete(
        run_id="test_cycle_001",
        products=["ceo_packet", "compliance_review"],
        errors=["LearnByDoing: test error"],
        runtime_min=12.3,
    )
    print(f"✅ notify_cycle_complete → sent={sent} (gate may suppress)")

    sent = notifier.notify_compliance_flag(
        strategy_name="Credit Builder Loan Strategy",
        status="needs_source_verification",
        reason="Lacks CFPB citation",
    )
    print(f"✅ notify_compliance_flag → sent={sent}")

    sent = notifier.notify_demo_order(
        instrument="EUR_USD",
        side="buy",
        units=1,
        ok=True,
        detail="fill price: 1.0825",
    )
    print(f"✅ notify_demo_order → sent={sent}")

    sent = notifier.notify_custom("Test custom notification from unit test", urgency="info")
    print(f"✅ notify_custom → sent={sent}")

    # Log file should exist
    assert NOTIFY_LOG.exists(), "Notification log not created"
    recent = notifier.recent_notifications(10)
    assert len(recent) >= 4, f"Expected >= 4 log entries, got {len(recent)}"
    print(f"✅ Notification log: {len(recent)} entries at {NOTIFY_LOG}")

    print("\n✅ Proactive notifier tests passed.")

if __name__ == "__main__":
    main()
