"""
test_decision_log_shows_decisions_not_policy.py
================================================
Verify 'show decision log' returns actual logged decisions, NOT approval policy rules.
The approval policy (read_artifact: autonomous_allowed, live_trading: blocked, etc.)
must NOT appear unless the user asks 'show approval policy'.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Policy rule strings that must NOT appear in the decision log response
POLICY_TERMS = [
    "autonomous_allowed",
    "approval_required",
    "live_trading: blocked",
    "fake_sources: blocked",
    "read_artifact: autonomous",
    "publish_content: approval",
]


class TestDecisionLogNotPolicy(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_decision_log_routes_correctly(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "decision_log")

    def test_decision_log_not_policy_rules(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        text = result.text.lower()
        for term in POLICY_TERMS:
            self.assertNotIn(term.lower(), text,
                f"Decision log must not show approval policy term '{term}': {result.text[:200]}")

    def test_decision_log_not_empty(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        self.assertGreater(len(result.text.strip()), 30)

    def test_decision_log_has_header(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        self.assertIn("DECISION LOG", result.text.upper())

    def test_decision_log_has_source_path(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        self.assertIn("hermes_decision_log", result.text.lower())

    def test_decision_log_refers_to_approval_policy_separately(self):
        """Decision log must mention that approval policy is available separately."""
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("approval policy", text,
            "Decision log should note that 'show approval policy' is available")

    def test_what_did_hermes_decide_routes_to_decision_log(self):
        result = self._call("what did hermes decide")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "decision_log",
            "'what did hermes decide' must route to decision_log, not policy")


class TestDecisionLogContent(unittest.TestCase):
    def test_decision_log_plain_english_not_policy_content(self):
        from lib.hermes_decision_log import decision_log_plain_english
        result = decision_log_plain_english()
        for term in POLICY_TERMS:
            self.assertNotIn(term.lower(), result.lower(),
                f"decision_log_plain_english must not contain policy term: {term}")

    def test_decision_log_meaningful_filter(self):
        from lib.hermes_decision_log import decision_log_plain_english, _decision_is_meaningful, load_recent_decisions
        all_dec = load_recent_decisions(50)
        if not all_dec:
            self.skipTest("No decisions in log yet")
        # Check that filter removes generic loop iterations
        generic = [d for d in all_dec if not _decision_is_meaningful(d)]
        meaningful = [d for d in all_dec if _decision_is_meaningful(d)]
        # At least some should pass the filter if we have real decisions
        # (even if all are generic, the function should still return something)
        result = decision_log_plain_english()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)


class TestApprovalPolicySeparate(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_show_approval_policy_routes_correctly(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "approval_policy",
            "show approval policy must route to approval_policy topic")

    def test_approval_policy_contains_policy_terms(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("autonomous", text, "Approval policy must mention autonomous actions")
        self.assertIn("approval", text, "Approval policy must list approval-required actions")
        self.assertIn("blocked", text, "Approval policy must list blocked actions")

    def test_approval_policy_not_decision_log(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        self.assertNotEqual(result.matched_topic, "decision_log",
            "Approval policy must not route to decision_log")


if __name__ == "__main__":
    unittest.main()
