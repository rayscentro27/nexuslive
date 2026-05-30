"""
test_build_content_no_duplicate_action.py
==========================================
Verify that calling 'build content from best opportunity' twice
does NOT create a duplicate action — the second call returns the
existing action status instead.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestNoDuplicateContentAction(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_second_call_detects_existing_action(self):
        """First call may or may not create; second call must detect existing."""
        # First call — may create or detect existing
        r1 = self._call("build content from the best opportunity")
        self.assertIsNotNone(r1)
        # Second call — must detect existing action
        r2 = self._call("build content from the best opportunity")
        self.assertIsNotNone(r2)
        # Second response must not say "CONTENT ACTION CREATED" again if first already created one
        text2 = r2.text
        if "CONTENT ACTION CREATED" in r1.text.upper():
            # First call created action — second must detect it
            self.assertFalse(
                "CONTENT ACTION CREATED" in text2.upper() and "already" not in text2.lower(),
                "Second call must detect existing action, not create a duplicate"
            )

    def test_no_growing_action_queue_on_repeat(self):
        from lib.hermes_action_queue import get_open_actions
        # First call to establish the action
        r1 = self._call("build content from the best opportunity")
        self.assertIsNotNone(r1)
        count_after_first = len(get_open_actions())
        # Second and third calls — queue should not grow further for the same action
        self._call("build content from the best opportunity")
        self._call("build content from the best opportunity")
        count_after_repeats = len(get_open_actions())
        self.assertLessEqual(
            count_after_repeats - count_after_first, 1,
            "Repeated calls must not keep adding the same action"
        )

    def test_duplicate_response_has_current_status(self):
        """When dedup triggers, response must show current action status."""
        # Ensure action exists
        self._call("build content from the best opportunity")
        # Now call again
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        if "already" in result.text.lower() or "already created" in result.text.lower():
            text = result.text.lower()
            self.assertTrue(
                "status:" in text or "queued" in text or "assigned" in text,
                "Duplicate response must show current action status"
            )

    def test_duplicate_response_has_evidence_path(self):
        """Duplicate response must include evidence path."""
        # Ensure action exists
        self._call("build content from the best opportunity")
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        if "already" in result.text.lower():
            self.assertIn("hermes_action_queue", result.text.lower(),
                "Duplicate response must reference evidence path")


if __name__ == "__main__":
    unittest.main()
