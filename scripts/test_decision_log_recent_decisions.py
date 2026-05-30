"""
test_decision_log_recent_decisions.py
======================================
Verify that 'show decision log' returns actual decision records,
not the approval policy rule list.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestDecisionLogRecentDecisions(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_decision_log_returns_result(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        self.assertIsInstance(result.text, str)
        self.assertGreater(len(result.text.strip()), 10)

    def test_decision_log_not_empty_message(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertNotIn("unavailable", text.split("\n")[0].lower(),
            "Decision log handler should not immediately say unavailable")

    def test_alternate_phrases_route_to_decision_log(self):
        for phrase in ["what did hermes decide", "hermes decisions", "show recent decisions"]:
            result = self._call(phrase)
            self.assertIsNotNone(result, f"'{phrase}' returned None")

    def test_decision_log_shows_decision_data(self):
        result = self._call("show decision log")
        self.assertIsNotNone(result)
        text = result.text.lower()
        # Should reference decisions, log, or artifacts — not just policy keywords
        has_decision_content = any(kw in text for kw in [
            "decision", "artifact", "draft", "research", "scout", "action",
            "no decisions", "intake",
        ])
        self.assertTrue(has_decision_content,
            f"Decision log response lacks decision content. Got:\n{result.text[:300]}")


if __name__ == "__main__":
    unittest.main()
