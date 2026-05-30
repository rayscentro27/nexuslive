"""
test_daily_intake_run_status_response.py
==========================================
Verify 'run daily opportunity intake' returns a clear status:
- manual_required: Hermes cannot start it inline, shows how to run
- Does NOT mix "queued" with a Python command
- Does NOT say "queued" when nothing was queued
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unittest

RUN_COMMANDS = [
    "run daily opportunity intake",
    "Hermes, run daily opportunity intake.",
    "run daily intake",
]

STATUS_KEYWORDS = ["manual", "queued", "running", "completed", "failed"]


class TestDailyIntakeRunStatus(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_run_commands_all_return_response(self):
        for cmd in RUN_COMMANDS:
            with self.subTest(cmd=cmd):
                result = self._call(cmd)
                self.assertIsNotNone(result, f"'{cmd}' returned None")
                self.assertGreater(len(result.text.strip()), 20)

    def test_run_command_has_clear_status(self):
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_status = any(kw in text for kw in STATUS_KEYWORDS)
        self.assertTrue(has_status,
            f"Response must contain a clear status (one of {STATUS_KEYWORDS}): {result.text[:200]}")

    def test_no_confusing_queued_plus_python(self):
        """Must not say 'queued' AND 'to run now: python3...' in the same message."""
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        text = result.text.lower()
        is_confusing = ("queued" in text and "python3" in text and "to run now" in text)
        self.assertFalse(is_confusing,
            "Response mixes 'queued' with 'to run now: python3...' — must choose one status")

    def test_manual_required_includes_command(self):
        """If status is manual_required, must include the actual command."""
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        text = result.text
        if "manual" in text.lower():
            self.assertIn("python3", text,
                "manual_required status must include the run command")

    def test_run_command_does_not_say_started_falsely(self):
        """Hermes cannot start inline — must not claim it has started."""
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        text = result.text.lower()
        falsely_started = (
            "is running now" in text and
            "python3" not in result.text and
            "manual" not in text
        )
        self.assertFalse(falsely_started,
            "Response claims running but no process was started")

    def test_anti_spam_mentioned(self):
        """Response should confirm anti-spam — one digest, not per-source."""
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertTrue(
            "digest" in text or "one" in text or "spam" in text or "updates" in text,
            "Response should confirm one-digest anti-spam policy"
        )

    def test_what_did_you_find_today_is_different_from_run(self):
        """'what did you find today' should NOT return the run acknowledgement."""
        run_result = self._call("run daily opportunity intake")
        status_result = self._call("what did you find today")
        self.assertIsNotNone(run_result)
        self.assertIsNotNone(status_result)
        self.assertNotEqual(run_result.text, status_result.text,
            "Run command and status query must return different responses")


if __name__ == "__main__":
    unittest.main()
