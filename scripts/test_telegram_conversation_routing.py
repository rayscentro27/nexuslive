"""
Test Telegram inbound conversation routing via HermesCollaboration.
Verifies new strategic routes added in Part 12 route to correct artifact keys.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from lib.hermes_collaboration_service import HermesCollaboration

def main():
    hermes = HermesCollaboration()

    route_tests = [
        # (message,                               expected_artifact_key)
        ("catch me up",                           "ceo_packet"),
        ("where are we right now",                "ceo_packet"),
        ("are we on track this week",             "ceo_packet"),
        ("show me pending handoffs",              "handoffs"),
        ("what do you need my approval on",       "handoffs"),
        ("what did Hermes decide on its own",     "decision_log"),
        ("what happened with the oanda demo",     "demo_exec"),
        ("show me the last demo order",           "demo_exec"),
        ("what's a free alternative to beehiiv", "premium_blockers"),
        ("what Telegram notifications did you send", "notifications"),
        ("show me recent notifications",          "notifications"),
        ("what did you learn about credit repair","credit_repair"),
        ("make money in 30 days",                 "30_day_plan"),
        ("continue research",                     "continued_research"),
        ("what mistake are you repeating",        "mistake_memory"),
    ]

    passed = failed = 0
    for message, expected_key in route_tests:
        result = hermes.handle(message)
        actual_key = result["artifact_key"]
        ok = actual_key == expected_key
        mark = "✅" if ok else "❌"
        print(f"{mark} '{message[:45]}' → {actual_key} (expected {expected_key})")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\nRouting: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
