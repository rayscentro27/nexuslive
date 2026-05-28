"""Test HermesActionHandoff and RayFeedbackStore."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from lib.hermes_action_handoff import HermesActionHandoff, RayFeedbackStore, HANDOFF_DIR, FEEDBACK_DIR

def main():
    handoff = HermesActionHandoff()
    feedback = RayFeedbackStore()

    # Create a handoff
    packet = handoff.create_handoff(
        title="Enable OANDA Demo Account",
        action_required="Set OANDA_DEMO_ENABLED=true in integrations/oanda_demo/.env",
        context="Hermes cannot place practice orders until Ray explicitly enables demo mode.",
        urgency="normal",
        artifacts=["integrations/oanda_demo/.env.example"],
        options=[
            {"label": "Approve", "description": "Set OANDA_DEMO_ENABLED=true", "consequence": "Hermes can place 1-unit practice orders (max 3/day)"},
            {"label": "Reject", "description": "Keep demo disabled", "consequence": "No demo orders placed"},
        ],
        run_id="test_001",
    )
    assert packet["status"] == "pending_ray"
    handoff_id = packet["handoff_id"]
    handoff_path = Path(packet["path"])
    assert handoff_path.exists(), f"Handoff not saved: {handoff_path}"
    print(f"✅ Handoff created: {handoff_path.name}")

    # Pending
    pending = handoff.pending_handoffs()
    assert any(h["handoff_id"] == handoff_id for h in pending), "Handoff not in pending list"
    print(f"✅ Pending handoffs: {len(pending)}")

    # Resolve
    resolved = handoff.resolve_handoff(handoff_id, "approved", resolution_note="Ray approved via Telegram")
    assert resolved is not None
    assert resolved["status"] == "approved"
    print(f"✅ Resolved handoff: {resolved['status']}")

    # Ray feedback
    fb = feedback.save("Test lesson: always run compliance before labeling client-safe", category="compliance", run_id="test_001")
    assert Path(fb["path"]).exists(), f"Feedback not saved: {fb['path']}"
    print(f"✅ Feedback saved: {Path(fb['path']).name}")

    recent = feedback.recent(5)
    assert len(recent) >= 1
    print(f"✅ Recent feedback: {len(recent)} items")

    print("\n✅ Action handoff and feedback tests passed.")

if __name__ == "__main__":
    main()
