"""Tests for Hermes language pack. Run: python3 tests/test_hermes_language_pack.py"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_language_pack as LP  # noqa: E402


class TestLanguagePack(unittest.TestCase):
    def test_small_talk_phrases(self):
        self.assertIn("how are you", LP.SMALL_TALK_PHRASES)
        self.assertIn("good morning", LP.SMALL_TALK_PHRASES)

    def test_capability_phrases(self):
        self.assertIn("what can you do", LP.CAPABILITY_PHRASES)
        self.assertIn("help", LP.CAPABILITY_PHRASES)

    def test_external_info_detection(self):
        self.assertTrue(LP.is_external_info("what is the weather"))
        self.assertTrue(LP.is_external_info("stock price of AAPL"))
        self.assertFalse(LP.is_external_info("what is nexus status"))

    def test_external_info_topic(self):
        topic = LP.external_info_topic("what is the weather today")
        self.assertEqual(topic, "weather")

    def test_external_unavailable_response(self):
        resp = LP.format_external_unavailable_response("weather")
        self.assertIn("weather", resp)
        self.assertIn("live", resp)

    def test_categories_defined(self):
        self.assertIn("small_talk", LP.ALL_CATEGORIES)
        self.assertIn("unknown_or_unresolved", LP.ALL_CATEGORIES)

    def test_gap_reason_codes(self):
        self.assertIn("missing_route", LP.GAP_MISSING_ROUTE)
        self.assertIn("unsupported_external", LP.GAP_UNSUPPORTED_EXTERNAL)


if __name__ == "__main__":
    unittest.main()
