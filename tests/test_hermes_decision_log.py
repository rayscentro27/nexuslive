"""Tests for Hermes decision log. Run: python3 tests/test_hermes_decision_log.py"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_decision_log as DL  # noqa: E402


class TestDecisionLog(unittest.TestCase):
    def tearDown(self):
        DL._LOG_JSONL.unlink(missing_ok=True)
        DL._LOG_MD.unlink(missing_ok=True)

    def test_log_decision_creates_entry(self):
        d = DL.log_decision(
            question_or_trigger="test trigger",
            decision="run tests",
            why_selected="verify behavior",
        )
        self.assertTrue(DL._LOG_JSONL.exists())
        self.assertIn("run tests", d.decision)
        lines = DL._LOG_JSONL.read_text().strip().splitlines()
        self.assertGreaterEqual(len(lines), 1)

    def test_log_decision_no_secrets(self):
        d = DL.log_decision(
            question_or_trigger="check secrets",
            decision="verify no leaks",
            why_selected="test",
        )
        text = json.dumps(d.to_dict())
        for secret in ("sk-", "api_key", "password", "token"):
            self.assertNotIn(secret, text.lower())

    def test_decision_has_id_and_timestamp(self):
        d = DL.log_decision(
            question_or_trigger="test",
            decision="verify structure",
            why_selected="test",
        )
        self.assertTrue(d.decision_id.startswith("dec_"))
        self.assertIsNotNone(d.timestamp)

    def test_decision_plain_english_format(self):
        d = DL.log_decision(
            question_or_trigger="test trigger",
            decision="verify format",
            why_selected="because",
        )
        text = d.to_plain_english()
        self.assertIn("verify format", text)
        self.assertIn("Trigger:", text)

    def test_latest_md_summary(self):
        DL.log_decision(
            question_or_trigger="test",
            decision="verify md summary",
            why_selected="test",
        )
        DL.write_latest_markdown()
        self.assertTrue(DL._LOG_MD.exists())
        summary = DL._LOG_MD.read_text()
        self.assertIn("verify md summary", summary)

    def test_multiple_decisions_appended(self):
        for i in range(3):
            DL.log_decision(
                question_or_trigger="test",
                decision=f"decision_{i}",
                why_selected=f"entry {i}",
            )
        lines = DL._LOG_JSONL.read_text().strip().splitlines()
        self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
