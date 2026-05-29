"""
test_daily_commands_no_raw_dump.py
=====================================
Verify Hermes does NOT dump raw artifact inventories or directory listings
by default for any daily cycle Telegram command.
Raw/technical output must only appear when Ray explicitly requests it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest

DAILY_COMMANDS = [
    "what did you find today",
    "show top monetization actions",
    "show rejected opportunities",
    "show daily research review",
    "what did you get your information from",
    "what needs my approval",
    "what scouts are working",
    "show rejected",
]

RAW_EVIDENCE_MARKERS = [
    "artifact_inventory",
    "items) —",
    "not yet created",
]


class TestNoRawEvidenceDump(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_daily_commands_no_raw_dump(self):
        for cmd in DAILY_COMMANDS:
            with self.subTest(cmd=cmd):
                result = self._call(cmd)
                if result is None:
                    continue  # command didn't route internally, that's ok
                for marker in RAW_EVIDENCE_MARKERS:
                    self.assertNotIn(
                        marker, result.text,
                        f"Command '{cmd}' contains raw evidence marker: '{marker}'"
                    )

    def test_information_sources_no_directory_dump(self):
        result = self._call("what did you get your information from")
        self.assertIsNotNone(result)
        text = result.text
        self.assertNotIn("items) —", text)
        self.assertNotIn("artifact_inventory", text)
        self.assertIn("YouTube", text)

    def test_rejected_no_raw_path(self):
        result = self._call("show rejected")
        self.assertIsNotNone(result)
        text = result.text
        self.assertFalse(
            "docs/reports/monetization/rejected_opportunities_" in text,
            "show rejected must not expose raw file paths"
        )

    def test_daily_review_human_readable_first(self):
        result = self._call("show daily research review")
        self.assertIsNotNone(result)
        text = result.text
        first_line = text.splitlines()[0] if text else ""
        self.assertFalse(
            first_line.startswith("/") or first_line.startswith("docs/"),
            f"First line must be human-readable, not a raw path. Got: {first_line}"
        )

    def test_technical_details_allowed_when_requested(self):
        result = self._call("show technical details")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "technical_details")


if __name__ == "__main__":
    unittest.main()
