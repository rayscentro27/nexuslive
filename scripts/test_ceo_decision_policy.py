"""Test HermesCEODecisionPolicy — classify all action categories."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1]))

from lib.hermes_ceo_decision_policy import HermesCEODecisionPolicy, DecisionClass

def main():
    policy = HermesCEODecisionPolicy()
    tests = [
        ("read_artifact",          DecisionClass.AUTONOMOUS_ALLOWED),
        ("run_validation_cycle",   DecisionClass.AUTONOMOUS_ALLOWED),
        ("publish_content",        DecisionClass.APPROVAL_REQUIRED),
        ("git_commit_push",        DecisionClass.APPROVAL_REQUIRED),
        ("live_trading",           DecisionClass.BLOCKED),
        ("oanda_live_env",         DecisionClass.BLOCKED),
        ("fake_sources",           DecisionClass.BLOCKED),
        ("unknown_mystery_action", DecisionClass.APPROVAL_REQUIRED),
    ]
    passed = failed = 0
    for action, expected in tests:
        result = policy.classify(action, context="unit_test")
        actual = result["decision"]
        ok = actual == expected.value
        mark = "✅" if ok else "❌"
        print(f"{mark} {action} → {actual} (expected {expected.value})")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    # Verify log file was written
    from lib.hermes_ceo_decision_policy import DECISION_LOG
    assert DECISION_LOG.exists(), "Decision log not created"
    count = len(DECISION_LOG.read_text().strip().splitlines())
    print(f"Decision log: {count} entries")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
