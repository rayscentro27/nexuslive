"""
test_continue_research_creates_real_actions.py
================================================
Verify "continue research while I am out" creates real action records
when HERMES_AUTONOMOUS_INTERNAL_ACTIONS=true, and stays dry-run when false.
Also verifies the response communicates safe-internal-only behavior.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


CONTINUE_COMMANDS = [
    "continue research while I am out",
    "Hermes, continue research while I am out.",
    "continue while i am out",
    "run the operating loop",
]


class TestContinueResearchEnabled(unittest.TestCase):
    """When HERMES_AUTONOMOUS_INTERNAL_ACTIONS=true (default)."""

    def setUp(self):
        os.environ["HERMES_AUTONOMOUS_INTERNAL_ACTIONS"] = "true"

    def tearDown(self):
        os.environ.pop("HERMES_AUTONOMOUS_INTERNAL_ACTIONS", None)

    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_continue_commands_all_return_response(self):
        for cmd in CONTINUE_COMMANDS:
            with self.subTest(cmd=cmd):
                result = self._call(cmd)
                self.assertIsNotNone(result, f"'{cmd}' returned None")
                self.assertGreater(len(result.text.strip()), 20)

    def test_operating_loop_called_with_dry_run_false(self):
        from lib.hermes_operating_loop import LoopResult
        mock_result = LoopResult(mode="continue")
        mock_result.digest = "Internal research complete. 2 actions created."
        mock_result.actions_created = ["act_abc123", "act_def456"]
        mock_result.artifact_path = ""
        with patch("lib.hermes_operating_loop.run_operating_loop", return_value=mock_result) as mock_loop:
            result = self._call("continue research while I am out")
            self.assertIsNotNone(result)
            call_kwargs = mock_loop.call_args[1] if mock_loop.call_args else {}
            call_args = mock_loop.call_args[0] if mock_loop.call_args else ()
            # dry_run should be False when HERMES_AUTONOMOUS_INTERNAL_ACTIONS=true
            dry_run_val = call_kwargs.get("dry_run", call_args[2] if len(call_args) > 2 else True)
            self.assertFalse(dry_run_val, "dry_run must be False when autonomous actions enabled")

    def test_operating_loop_mode_is_continue(self):
        from lib.hermes_operating_loop import LoopResult
        mock_result = LoopResult(mode="continue")
        mock_result.digest = "Continue mode active."
        mock_result.actions_created = []
        mock_result.artifact_path = ""
        with patch("lib.hermes_operating_loop.run_operating_loop", return_value=mock_result) as mock_loop:
            self._call("continue research while I am out")
            call_kwargs = mock_loop.call_args[1] if mock_loop.call_args else {}
            mode_val = call_kwargs.get("mode", "")
            self.assertEqual(mode_val, "continue",
                "mode must be 'continue' when autonomous actions enabled")

    def test_response_does_not_say_dry_run(self):
        result = self._call("continue research while I am out")
        self.assertIsNotNone(result)
        self.assertNotIn("dry-run", result.text.lower(),
            "Response must not mention dry-run when autonomous actions enabled")

    def test_response_confirms_no_publish_spend_trade(self):
        result = self._call("continue research while I am out")
        self.assertIsNotNone(result)
        text = result.text.lower()
        safe_terms = ["internal", "draft", "no publishing", "no cost", "approval", "digest"]
        self.assertTrue(
            any(t in text for t in safe_terms),
            f"Response must confirm safe-internal-only behavior: {result.text[:200]}"
        )


class TestContinueResearchDisabled(unittest.TestCase):
    """When HERMES_AUTONOMOUS_INTERNAL_ACTIONS=false."""

    def setUp(self):
        os.environ["HERMES_AUTONOMOUS_INTERNAL_ACTIONS"] = "false"

    def tearDown(self):
        os.environ.pop("HERMES_AUTONOMOUS_INTERNAL_ACTIONS", None)

    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_operating_loop_called_with_dry_run_true(self):
        from lib.hermes_operating_loop import LoopResult
        mock_result = LoopResult(mode="validation")
        mock_result.digest = "Validation run (dry-run)."
        mock_result.actions_created = ["[DRY RUN] Action A"]
        mock_result.artifact_path = ""
        with patch("lib.hermes_operating_loop.run_operating_loop", return_value=mock_result) as mock_loop:
            self._call("continue research while I am out")
            call_kwargs = mock_loop.call_args[1] if mock_loop.call_args else {}
            dry_run_val = call_kwargs.get("dry_run", False)
            self.assertTrue(dry_run_val, "dry_run must be True when autonomous actions disabled")

    def test_response_mentions_validation_or_dry_run(self):
        result = self._call("continue research while I am out")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertTrue(
            "validation" in text or "dry-run" in text or "autonomous" in text,
            "Must mention validation/dry-run mode when disabled"
        )


if __name__ == "__main__":
    unittest.main()
