"""
test_show_approval_policy_separate.py
=======================================
Verify 'show approval policy' is a distinct command from decision log,
returns CEO decision policy rules in plain language.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

APPROVAL_POLICY_COMMANDS = [
    "show approval policy",
    "what can you do autonomously",
    "what is blocked",
    "what requires my approval",
    "hermes policy",
]


class TestApprovalPolicyRouting(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_all_commands_route_to_approval_policy(self):
        for cmd in APPROVAL_POLICY_COMMANDS:
            with self.subTest(cmd=cmd):
                result = self._call(cmd)
                self.assertIsNotNone(result, f"'{cmd}' returned None")
                self.assertEqual(result.matched_topic, "approval_policy",
                    f"'{cmd}' routed to '{result.matched_topic}', not 'approval_policy'")

    def test_approval_policy_not_routed_to_decision_log(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        self.assertNotEqual(result.matched_topic, "decision_log")

    def test_approval_policy_not_routed_to_needs_approval(self):
        # "show approval policy" is different from "show approval needed"
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        self.assertNotEqual(result.matched_topic, "needs_approval")


class TestApprovalPolicyContent(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_has_approval_policy_header(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        self.assertIn("APPROVAL POLICY", result.text.upper())

    def test_lists_autonomous_actions(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("autonomous", text, "Must list autonomous actions")
        self.assertIn("read_artifact", text, "Must include read_artifact as autonomous")

    def test_lists_approval_required_actions(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("approval", text)
        self.assertIn("publish_content", text, "Must include publish_content as approval_required")

    def test_lists_blocked_actions(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("blocked", text)
        self.assertIn("live_trading", text, "Must include live_trading as blocked")

    def test_uses_ceo_decision_policy_source(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        self.assertEqual(result.source, "hermes_ceo_decision_policy")

    def test_decision_log_and_approval_policy_return_different_content(self):
        dl_result = self._call("show decision log")
        ap_result = self._call("show approval policy")
        self.assertIsNotNone(dl_result)
        self.assertIsNotNone(ap_result)
        self.assertNotEqual(dl_result.text[:100], ap_result.text[:100],
            "Decision log and approval policy must return different content")


if __name__ == "__main__":
    unittest.main()
