"""Tests for Hermes CFO doctrine loader. Run: python3 tests/test_hermes_cfo_doctrine.py"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_cfo_doctrine as CD  # noqa: E402


class TestCfoDoctrine(unittest.TestCase):
    def test_doctrine_files_mapped(self):
        self.assertIn("cfo_conversation", CD._DOCTRINE_FILES)
        self.assertIn("plain_language", CD._DOCTRINE_FILES)
        self.assertIn("unknown_answer", CD._DOCTRINE_FILES)
        self.assertIn("scout_dispatch", CD._DOCTRINE_FILES)

    def test_behavior_rules_summary(self):
        self.assertIn("Ray's CFO/operator", CD._BEHAVIOR_RULES_SUMMARY)

    def test_load_cfo_doctrine_returns_dict(self):
        result = CD.load_cfo_doctrine()
        self.assertIsInstance(result, dict)
        self.assertIn("cfo_conversation", result)

    def test_doctrine_files_exist_check(self):
        exists = CD.doctrine_files_exist()
        self.assertIsInstance(exists, dict)
        self.assertIn("cfo_conversation", exists)

    def test_get_cfo_behavior_rules(self):
        rules = CD.get_cfo_behavior_rules()
        self.assertIsNotNone(rules)
        self.assertIn("Ray", rules)

    def test_get_plain_language_rules(self):
        rules = CD.get_plain_language_rules()
        self.assertIsNotNone(rules)


if __name__ == "__main__":
    unittest.main()
