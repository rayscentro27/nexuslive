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


class TestCfoBrainOptionalDeps(unittest.TestCase):
    """Optional helper modules (hermes_tool_chooser, hermes_failure_learning) may not
    be present yet. Handlers must degrade deterministically, never raise ImportError,
    and never claim a tool ran or a failure was saved when the module is absent."""

    @staticmethod
    def _force_absent(modname):
        """Context-like helper: make `from <modname> import ...` raise ImportError.
        Returns a restore() callable."""
        sentinel = object()
        saved = sys.modules.get(modname, sentinel)
        sys.modules[modname] = None  # Python raises ImportError on import of a None entry

        def restore():
            if saved is sentinel:
                sys.modules.pop(modname, None)
            else:
                sys.modules[modname] = saved
        return restore

    def test_tool_chooser_returns_none_when_absent(self):
        restore = self._force_absent("lib.hermes_tool_chooser")
        try:
            self.assertIsNone(CB._tool_chooser())
        finally:
            restore()

    def test_morning_activity_fallback_when_tool_chooser_absent(self):
        restore = self._force_absent("lib.hermes_tool_chooser")
        try:
            out = CB.handle_morning_activity("what did you do this morning", {})
            self.assertIsInstance(out, str)               # no ImportError
            self.assertIn("Tool chooser unavailable", out)  # deterministic, honest
        finally:
            restore()

    def test_queue_status_fallback_when_tool_chooser_absent(self):
        restore = self._force_absent("lib.hermes_tool_chooser")
        try:
            out = CB.handle_queue_status("what tasks are in the queue", {})
            self.assertIsInstance(out, str)
            self.assertIn("Tool chooser unavailable", out)
        finally:
            restore()

    def test_morning_activity_uses_tool_chooser_when_present(self):
        import types
        fake = types.ModuleType("lib.hermes_tool_chooser")
        fake.execute_chosen_tool = lambda tool, msg, ctx: (
            "SENTINEL_MORNING" if tool == "morning_activity" else "")
        sentinel = object()
        saved = sys.modules.get("lib.hermes_tool_chooser", sentinel)
        sys.modules["lib.hermes_tool_chooser"] = fake
        try:
            out = CB.handle_morning_activity("what did you do this morning", {})
            self.assertIsInstance(out, str)
            self.assertNotIn("Tool chooser unavailable", out)  # present path preserved
        finally:
            if saved is sentinel:
                sys.modules.pop("lib.hermes_tool_chooser", None)
            else:
                sys.modules["lib.hermes_tool_chooser"] = saved

    def test_log_failed_response_safe_noop_when_absent(self):
        restore = self._force_absent("lib.hermes_failure_learning")
        try:
            res = CB._log_failed_response_safe(message="m", response="r", reason="x")
            self.assertIsInstance(res, dict)
            self.assertFalse(res.get("logged"))            # never claims a save
            self.assertIn("unavailable", res.get("status", ""))
        finally:
            restore()

    def test_failure_feedback_no_import_error_when_absent(self):
        restore = self._force_absent("lib.hermes_failure_learning")
        try:
            out = CB.handle_failure_feedback(
                "that is not what i meant", {"last_user_message": "do x"})
            self.assertIsInstance(out, str)               # no ImportError raised
        finally:
            restore()


if __name__ == "__main__":
    unittest.main()
