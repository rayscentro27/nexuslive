"""
test_daily_intake_command_ack.py
==================================
Verify 'run daily opportunity intake' returns an immediate acknowledgement.
It must NOT silently show old state or return empty.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


class TestDailyIntakeCommandAck(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_run_daily_intake_returns_acknowledgement(self):
        result = self._call("Hermes, run daily opportunity intake")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertTrue(
            "queued" in text or "running" in text or "collecting" in text or "intake" in text,
            f"Expected acknowledgement, got: {result.text[:200]}"
        )

    def test_run_daily_intake_not_empty(self):
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        self.assertTrue(len(result.text) > 20, "Response too short")

    def test_run_daily_intake_does_not_say_no_data(self):
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        # Should not just dump "no data" when user said run
        text = result.text.lower()
        self.assertNotIn("no data collected", text,
            "Should not say 'no data' when user asked to run — should acknowledge instead")

    def test_run_daily_intake_includes_how_to_run(self):
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        # Should include instructions
        text = result.text
        self.assertTrue(
            "python3" in text or "script" in text or "1-2 minutes" in text or "queued" in text,
            f"Expected run instructions or queue confirmation, got: {text[:200]}"
        )

    def test_what_did_you_find_today_shows_status(self):
        """'what did you find today' should show existing cycle status, not run acknowledgement."""
        result = self._call("what did you find today")
        self.assertIsNotNone(result)
        text = result.text.lower()
        # Should NOT show "queued" or "collecting" — that's for the run command
        self.assertFalse(
            text.startswith("daily opportunity intake queued"),
            "Status query should not look like run acknowledgement"
        )

    def test_run_daily_intake_has_matched_topic(self):
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "daily_intake")

    def test_sources_pending_shows_status_not_ack(self):
        result = self._call("what sources are pending")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertFalse(
            "queued" in text and "1-2 minutes" in text,
            "Pending sources query should not show run acknowledgement"
        )


if __name__ == "__main__":
    unittest.main()
