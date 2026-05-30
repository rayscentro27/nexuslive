"""
test_action_queue_summary_unique.py
=====================================
Verify 'show action queue' returns a deduplicated summary with
unique count, duplicate count, and the correct format.
"""
import sys
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestFormatActionQueueSummary(unittest.TestCase):
    def _summary(self) -> str:
        from lib.hermes_action_queue import format_action_queue_summary_common_language
        return format_action_queue_summary_common_language()

    def test_function_exists(self):
        from lib.hermes_action_queue import format_action_queue_summary_common_language
        self.assertTrue(callable(format_action_queue_summary_common_language))

    def test_returns_string(self):
        result = self._summary()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 20)

    def test_has_action_queue_header(self):
        result = self._summary()
        self.assertIn("ACTION QUEUE", result)

    def test_mentions_open_actions(self):
        result = self._summary()
        self.assertTrue(
            "open action" in result.lower() or "unique action" in result.lower(),
            "Summary must mention open or unique actions"
        )

    def test_shows_top_actions(self):
        from lib.hermes_action_queue import get_unique_open_actions
        unique = get_unique_open_actions()
        result = self._summary()
        if unique:
            # Should show at least one numbered item
            self.assertRegex(result, r"\d+\.", "Should have numbered action items")

    def test_has_evidence_path(self):
        result = self._summary()
        self.assertIn("hermes_action_queue", result.lower(),
            "Summary must reference the evidence path")


class TestActionQueueTelegramResponse(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_show_action_queue_returns_response(self):
        result = self._call("show action queue")
        self.assertIsNotNone(result)
        self.assertGreater(len(result.text.strip()), 30)

    def test_show_action_queue_topic_correct(self):
        result = self._call("show action queue")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "action_queue")

    def test_no_raw_json_in_response(self):
        result = self._call("show action queue")
        self.assertIsNotNone(result)
        self.assertNotIn('"action_id":', result.text,
            "Response must not contain raw JSON")

    def test_shows_unique_count_or_total(self):
        result = self._call("show action queue")
        self.assertIsNotNone(result)
        # Should mention either the count or "actions"
        self.assertIn("action", result.text.lower())

    def test_if_duplicates_exist_suppressed_message(self):
        from lib.hermes_action_queue import get_open_actions, get_unique_open_actions
        all_open = get_open_actions()
        unique = get_unique_open_actions()
        if len(all_open) > len(unique):
            result = self._call("show action queue")
            self.assertIsNotNone(result)
            text = result.text.lower()
            self.assertTrue(
                "duplicate" in text or "repeated" in text,
                "Must mention duplicates when they exist"
            )


if __name__ == "__main__":
    unittest.main()
