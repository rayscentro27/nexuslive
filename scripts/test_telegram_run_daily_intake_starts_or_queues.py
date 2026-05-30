"""
test_telegram_run_daily_intake_starts_or_queues.py
====================================================
Verify "run daily opportunity intake" starts or queues the intake
when HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN=true, and falls back
to manual_required when the flag is false.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


RUN_COMMANDS = [
    "run daily opportunity intake",
    "Hermes, run daily opportunity intake.",
    "run daily intake",
]


class TestRunDailyIntakeEnabled(unittest.TestCase):
    """When HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN=true (default)."""

    def setUp(self):
        os.environ["HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN"] = "true"
        os.environ["HERMES_INTERNAL_ACTION_MODE"] = "true"

    def tearDown(self):
        os.environ.pop("HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN", None)
        os.environ.pop("HERMES_INTERNAL_ACTION_MODE", None)

    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_run_commands_return_response(self):
        for cmd in RUN_COMMANDS:
            with self.subTest(cmd=cmd):
                with patch("subprocess.Popen") as mock_popen:
                    result = self._call(cmd)
                    self.assertIsNotNone(result, f"'{cmd}' returned None")

    def test_run_command_launches_subprocess(self):
        with patch("subprocess.Popen") as mock_popen:
            result = self._call("run daily opportunity intake")
            self.assertIsNotNone(result)
            mock_popen.assert_called_once()

    def test_run_command_not_manual_required(self):
        with patch("subprocess.Popen"):
            result = self._call("run daily opportunity intake")
            self.assertIsNotNone(result)
            text = result.text.lower()
            self.assertNotIn("manual command required", text,
                "When flag enabled, must not say manual command required")

    def test_run_command_says_running(self):
        with patch("subprocess.Popen"):
            result = self._call("run daily opportunity intake")
            self.assertIsNotNone(result)
            text = result.text.lower()
            self.assertIn("running", text,
                "Response must confirm intake is running")

    def test_run_command_anti_spam_confirmed(self):
        with patch("subprocess.Popen"):
            result = self._call("run daily opportunity intake")
            self.assertIsNotNone(result)
            text = result.text.lower()
            self.assertTrue(
                "digest" in text or "one" in text or "updates" in text,
                "Must confirm one-digest anti-spam policy"
            )

    def test_subprocess_uses_validation_mode(self):
        with patch("subprocess.Popen") as mock_popen:
            self._call("run daily opportunity intake")
            call_args = mock_popen.call_args
            self.assertIsNotNone(call_args)
            cmd_args = call_args[0][0]
            self.assertIn("--mode", cmd_args)
            self.assertIn("validation", cmd_args)

    def test_subprocess_devnull_stdout(self):
        """Subprocess must not inherit stdout — would block Telegram response."""
        import subprocess
        with patch("subprocess.Popen") as mock_popen:
            self._call("run daily opportunity intake")
            call_kwargs = mock_popen.call_args[1]
            self.assertEqual(call_kwargs.get("stdout"), subprocess.DEVNULL,
                "stdout must be DEVNULL to avoid blocking")


class TestRunDailyIntakeDisabled(unittest.TestCase):
    """When HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN=false."""

    def setUp(self):
        os.environ["HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN"] = "false"

    def tearDown(self):
        os.environ.pop("HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN", None)

    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_disabled_returns_manual_required(self):
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        self.assertIn("manual", result.text.lower())

    def test_disabled_includes_python_command(self):
        result = self._call("run daily opportunity intake")
        self.assertIsNotNone(result)
        self.assertIn("python3", result.text)

    def test_disabled_no_subprocess_launched(self):
        with patch("subprocess.Popen") as mock_popen:
            self._call("run daily opportunity intake")
            mock_popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
