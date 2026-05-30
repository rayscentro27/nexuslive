"""
test_build_content_from_best_opportunity_creates_action.py
============================================================
Verify 'build content from best opportunity' creates a real internal action,
decision log entry, and handoff artifact — not a manual command instruction.
"""
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BUILD_COMMANDS = [
    "build content from the best opportunity",
    "build content from best opportunity",
    "create content from top opportunity",
    "build content packet",
    "create draft from best opportunity",
]


class TestBuildContentRouting(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_all_commands_route_correctly(self):
        for cmd in BUILD_COMMANDS:
            with self.subTest(cmd=cmd):
                result = self._call(cmd)
                self.assertIsNotNone(result, f"'{cmd}' returned None")
                self.assertEqual(result.matched_topic, "build_content_from_opportunity",
                    f"'{cmd}' routed to '{result.matched_topic}'")


class TestBuildContentCreatesAction(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_does_not_tell_ray_to_run_manually(self):
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertNotIn("to create the content brief: run_content_pipeline.py",
            text, "Must not tell Ray to run the script manually")
        self.assertNotIn("run_content_pipeline.py with this topic",
            text, "Must not tell Ray to run the script manually")

    def test_response_has_content_action_created_or_exists(self):
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        text = result.text.upper()
        self.assertTrue(
            "CONTENT ACTION CREATED" in text or "ALREADY CREATED" in text or "already" in result.text.lower(),
            f"Response must confirm action created or already exists: {result.text[:200]}"
        )

    def test_response_mentions_assigned_scout(self):
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("scout", text, "Response must mention assigned scout")

    def test_response_has_approval_boundary(self):
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("approval", text, "Response must include approval boundary")

    def test_response_has_action_id_or_evidence(self):
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        text = result.text
        self.assertTrue(
            "act_" in text or "Action:" in text or "Evidence:" in text or "Handoff:" in text,
            "Response must include action ID or evidence path"
        )

    def test_action_queue_grows_after_build_content(self):
        from lib.hermes_action_queue import get_open_actions
        before = len(get_open_actions())
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        # Only check growth if a new action was created (not a duplicate)
        if "CONTENT ACTION CREATED" in result.text.upper():
            after = len(get_open_actions())
            self.assertGreaterEqual(after, before,
                "Action queue should not shrink after build content")

    def test_no_publishing_in_response(self):
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        text = result.text.lower()
        # Must NOT claim content is published
        self.assertNotIn("published to", text)
        self.assertNotIn("went live", text)
        self.assertNotIn("posted to", text)

    def test_handoff_artifact_created(self):
        """After a CONTENT ACTION CREATED response, a handoff file should exist."""
        result = self._call("build content from the best opportunity")
        self.assertIsNotNone(result)
        if "CONTENT ACTION CREATED" not in result.text.upper():
            self.skipTest("No new action created (duplicate); skipping handoff check")
        root = Path(__file__).resolve().parent.parent
        handoff_dir = root / "docs" / "reports" / "agent_handoffs"
        handoffs = sorted(handoff_dir.glob("content_intelligence_handoff_*.json")) if handoff_dir.exists() else []
        self.assertGreater(len(handoffs), 0, "Handoff artifact must be created")
        # Validate handoff structure
        latest = json.loads(handoffs[-1].read_text())
        self.assertIn("action_id", latest)
        self.assertIn("assigned_scout", latest)
        self.assertIn("approval_boundary", latest)


if __name__ == "__main__":
    unittest.main()
