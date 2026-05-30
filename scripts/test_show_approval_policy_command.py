"""
test_show_approval_policy_command.py
=====================================
Verify that 'show approval policy' and related phrases return the correct
plain-language policy response and are NOT swallowed by LLM fallback.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REQUIRED_SECTIONS = [
    "autonomous allowed",
    "ray approval required",
    "blocked",
]

_POLICY_CONTENT_WORDS = [
    "research", "draft", "publishing", "approval",
]

_BANNED_IN_POLICY = [
    "run_validation_cycle",
    "read_artifact",
    "run_compliance_review",
]


class TestShowApprovalPolicyCommand(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_approval_policy_returns_result(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        self.assertGreater(len(result.text.strip()), 50)

    def test_approval_policy_has_required_sections(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        for section in _REQUIRED_SECTIONS:
            self.assertIn(section, text,
                f"Approval policy must contain section '{section}'")

    def test_approval_policy_has_plain_language(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_content = any(w in text for w in _POLICY_CONTENT_WORDS)
        self.assertTrue(has_content,
            f"Approval policy must contain plain language. Got:\n{result.text[:300]}")

    def test_approval_policy_no_technical_action_names(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text
        for term in _BANNED_IN_POLICY:
            self.assertNotIn(term, text,
                f"Approval policy must not show raw action names like '{term}' in the plain-language response")

    def test_alternate_phrases_route_to_policy(self):
        for phrase in [
            "what can you do autonomously",
            "what can you do without approval",
            "hermes policy",
        ]:
            result = self._call(phrase)
            self.assertIsNotNone(result, f"'{phrase}' returned None")
            if result:
                text = result.text.lower()
                has_policy = any(s in text for s in _REQUIRED_SECTIONS)
                self.assertTrue(has_policy, f"'{phrase}' must return policy content")

    def test_approval_policy_has_blocked_section(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("blocked", text,
            "Approval policy must list blocked actions")
        has_block_content = any(kw in text for kw in ["fake", "money", "trading", "live"])
        self.assertTrue(has_block_content, "Blocked section must list specific blocked actions")

    def test_approval_policy_mentions_publishing_requirement(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("publishing", text,
            "Approval policy must explicitly mention 'publishing' requires approval")

    def test_what_needs_my_approval_routes_correctly(self):
        result = self._call("what needs my approval")
        self.assertIsNotNone(result)

    def test_approval_policy_not_empty_fallback(self):
        result = self._call("show approval policy")
        self.assertIsNotNone(result)
        text = result.text.strip()
        self.assertNotEqual(text, "Approval policy unavailable.",
            "Must not return the unavailable fallback when handler is working")


if __name__ == "__main__":
    unittest.main()
