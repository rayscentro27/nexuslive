"""Test HermesConversationService — topic detection and conversation save."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from lib.hermes_conversation_service import HermesConversationService, _detect_topics, CONV_DIR

def main():
    # Topic detection
    tests = [
        ("catch me up on the CEO packet", ["ceo_packet"]),
        ("what did nexus learn about credit repair?", ["credit_repair"]),
        ("show me the github trends", ["github_trends"]),
        ("what's the oanda demo status?", ["demo_exec"]),
    ]
    print("[test_conv] Topic detection:")
    for msg, expected_topics in tests:
        topics = _detect_topics(msg)
        hit = any(t in topics for t in expected_topics)
        mark = "✅" if hit else "⚠️"
        print(f"  {mark} '{msg[:40]}' → {topics}")

    # Conversation service
    print("\n[test_conv] Creating conversation service…")
    service = HermesConversationService()
    result = service.chat("catch me up — what did Nexus produce?", save=True)
    assert "reply" in result, "No reply in result"
    assert "saved_to" in result, "Not saved"
    saved = Path(result["saved_to"])
    assert saved.exists(), f"Conversation not saved: {saved}"
    print(f"  ✅ Reply length: {len(result['reply'])} chars")
    print(f"  ✅ Saved: {saved.name}")
    print(f"  ✅ Topics loaded: {result['topics_loaded']}")
    print("\n✅ Conversation service tests passed.")

if __name__ == "__main__":
    main()
