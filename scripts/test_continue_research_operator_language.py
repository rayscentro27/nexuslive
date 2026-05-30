"""
test_continue_research_operator_language.py
=============================================
Verify that 'continue research while I am out' returns operator-language
output (what Hermes will focus on, what needs approval) instead of a
count-heavy validation report.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REPORT_PHRASES = [
    "goals: ",
    "scouts: ",
    "artifacts: ",
    "open actions: ",
    "validation report",
    "6 goals",
    "28 scouts",
    "120 artifacts",
    "69 open actions",
]

_OPERATOR_PHRASES = [
    "research",
    "approval",
    "draft",
    "review",
    "digest",
    "focusing on",
    "message",
]


class TestContinueResearchOperatorLanguage(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_continue_research_returns_result(self):
        result = self._call("continue research while I am out")
        self.assertIsNotNone(result)
        self.assertIsInstance(result.text, str)
        self.assertGreater(len(result.text.strip()), 20)

    def test_continue_research_not_a_count_report(self):
        result = self._call("continue research while I am out")
        self.assertIsNotNone(result)
        text = result.text.lower()
        for phrase in _REPORT_PHRASES:
            self.assertNotIn(phrase.lower(), text,
                f"'continue research' must not output count report phrase '{phrase}'")

    def test_continue_research_has_operator_language(self):
        result = self._call("continue research while I am out")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_operator_lang = any(phrase in text for phrase in _OPERATOR_PHRASES)
        self.assertTrue(has_operator_lang,
            f"'continue research' must use operator language. Got:\n{result.text[:300]}")

    def test_continue_research_mentions_approval_boundary(self):
        result = self._call("continue research while I am out")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_boundary = any(kw in text for kw in ["approval", "approve", "without approval", "needs your"])
        self.assertTrue(has_boundary,
            "Response must mention what requires approval vs. what can run autonomously")

    def test_alternate_phrase_routes_correctly(self):
        for phrase in ["continue research while i'm away", "keep working on research"]:
            result = self._call(phrase)
            # These phrases may not be wired — just check they don't produce count reports
            if result:
                text = result.text.lower()
                for bad in _REPORT_PHRASES:
                    self.assertNotIn(bad.lower(), text,
                        f"'{phrase}' response must not contain count report phrase '{bad}'")


if __name__ == "__main__":
    unittest.main()
