"""Tests for Hermes CFO brain. Run: python3 tests/test_hermes_cfo_brain.py"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_cfo_brain as CB  # noqa: E402


class TestCfoBrain(unittest.TestCase):
    def test_safety_boundary_present(self):
        self.assertIsNotNone(CB._SAFETY_BOUNDARY)
        self.assertIn("explicit Ray approval", CB._SAFETY_BOUNDARY)

    def test_intent_categories_defined(self):
        self.assertIn("followup_question", CB.CFO_BRAIN_INTENTS)
        self.assertIn("option_selection", CB.CFO_BRAIN_INTENTS)
        self.assertIn("simplify_previous_response", CB.CFO_BRAIN_INTENTS)

    def test_classify_followup(self):
        intent = CB.classify_cfo_intent("tell me more about that")
        self.assertEqual(intent, "followup_question")

    def test_classify_simplify(self):
        intent = CB.classify_cfo_intent("simplify that")
        self.assertEqual(intent, "simplify_previous_response")

    def test_classify_explain(self):
        intent = CB.classify_cfo_intent("explain that")
        self.assertEqual(intent, "explain_previous_response")

    def test_classify_general_conversation(self):
        intent = CB.classify_cfo_intent("asdfghjkl random noise")
        self.assertEqual(intent, "general_business_conversation")

    def test_no_live_actions_in_intents(self):
        for intent in CB.CFO_BRAIN_INTENTS:
            self.assertNotIn("publish", intent)
            self.assertNotIn("deploy", intent)
            self.assertNotIn("trade", intent)
            self.assertNotIn("email", intent)

    def test_should_use_cfo_brain_long_message(self):
        self.assertTrue(CB.should_use_cfo_brain("what do you think about this opportunity we found"))

    def test_should_not_use_cfo_brain_short_message(self):
        self.assertFalse(CB.should_use_cfo_brain("hi"))

    def test_should_not_use_for_command_verb(self):
        self.assertFalse(CB.should_use_cfo_brain("show tasks"))

    def test_format_cfo_brain_response_includes_content(self):
        result = CB.format_cfo_brain_response("test response", "followup_question")
        self.assertIn("test response", result)

    def test_classify_option_selection(self):
        intent = CB.classify_cfo_intent("option 1")
        self.assertEqual(intent, "option_selection")

    def test_classify_money_strategy(self):
        intent = CB.classify_cfo_intent("how do we make money this week")
        self.assertEqual(intent, "money_strategy_question")


if __name__ == "__main__":
    unittest.main()
