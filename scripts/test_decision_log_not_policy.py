"""
test_decision_log_not_policy.py
================================
Verify that 'show decision log' does NOT show approval policy rules
(read_artifact, run_validation_cycle, publish_content, live_trading, fake_sources).
These should only appear under 'show approval policy'.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_POLICY_RULE_KEYWORDS = [
    "run_validation_cycle",
    "publish_content",
    "live_trading",
    "fake_sources",
    "autonomous_allowed",
    "requires_ray_approval",
]


class TestDecisionLogNotPolicy(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_decision_log_does_not_contain_policy_rules(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        text = result.text
        for rule in _POLICY_RULE_KEYWORDS:
            self.assertNotIn(rule, text,
                f"'show decision log' must not show policy rule '{rule}'. "
                f"Use 'show approval policy' for that.")

    def test_approval_policy_contains_policy_rules(self):
        """'show approval policy' is allowed to contain policy rules."""
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        # Must contain at least one policy indicator
        text = result.text.lower()
        has_policy = any(kw in text for kw in [
            "approval", "autonomous", "allowed", "policy", "publish",
        ])
        self.assertTrue(has_policy,
            f"'show approval policy' must describe policy. Got:\n{result.text[:300]}")

    def test_decision_log_and_policy_are_distinct(self):
        """Decision log and approval policy should return different responses."""
        log_result = self._call("show decision log")
        policy_result = self._call("show approval policy")
        self.assertIsNotNone(log_result)
        self.assertIsNotNone(policy_result)
        self.assertNotEqual(
            log_result.text.strip()[:80],
            policy_result.text.strip()[:80],
            "Decision log and approval policy must return different responses"
        )


if __name__ == "__main__":
    unittest.main()
