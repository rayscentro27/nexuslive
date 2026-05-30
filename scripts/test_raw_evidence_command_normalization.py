"""
test_raw_evidence_command_normalization.py
============================================
Verify normalization strips smart quotes, em dashes, bullets so copied menu
items route to raw_evidence topic and return artifact paths.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unittest


RAW_EVIDENCE_VARIANTS = [
    "show raw evidence",
    "'show raw evidence'",
    '"show raw evidence"',
    "‘show raw evidence’",        # curly single quotes
    "“show raw evidence”",        # curly double quotes
    "‘show raw evidence’ — artifact files and paths",  # with em dash suffix
    "• show raw evidence — artifact files and paths",
    "  'show raw evidence' — artifact files and paths  ",
    "raw evidence",
]


class TestNormalizationFunction(unittest.TestCase):
    def _norm(self, text: str) -> str:
        from lib.hermes_internal_first import _normalize_input
        return _normalize_input(text)

    def test_strips_single_quotes(self):
        self.assertEqual(self._norm("'show raw evidence'"), "show raw evidence")

    def test_strips_double_quotes(self):
        self.assertEqual(self._norm('"show raw evidence"'), "show raw evidence")

    def test_strips_curly_single_quotes(self):
        self.assertEqual(self._norm("‘show raw evidence’"), "show raw evidence")

    def test_strips_curly_double_quotes(self):
        self.assertEqual(self._norm("“show raw evidence”"), "show raw evidence")

    def test_strips_em_dash_and_description(self):
        self.assertEqual(self._norm("show raw evidence — artifact files and paths"),
                         "show raw evidence")

    def test_strips_en_dash_and_description(self):
        self.assertEqual(self._norm("show raw evidence – artifact files and paths"),
                         "show raw evidence")

    def test_strips_bullet(self):
        self.assertEqual(self._norm("• show raw evidence"), "show raw evidence")

    def test_strips_combined(self):
        self.assertEqual(
            self._norm("‘show raw evidence’ — artifact files and paths"),
            "show raw evidence"
        )

    def test_preserves_normal_text(self):
        self.assertEqual(self._norm("what did you find today"), "what did you find today")

    def test_strips_whitespace(self):
        self.assertEqual(self._norm("  show raw evidence  "), "show raw evidence")


class TestRawEvidenceRouting(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_all_variants_route_to_raw_evidence(self):
        for variant in RAW_EVIDENCE_VARIANTS:
            with self.subTest(variant=variant):
                result = self._call(variant)
                self.assertIsNotNone(result, f"'{variant}' returned None")
                self.assertEqual(
                    result.matched_topic, "raw_evidence",
                    f"'{variant}' routed to '{result.matched_topic}' not 'raw_evidence'"
                )

    def test_raw_evidence_not_technical_details_menu(self):
        result = self._call("show raw evidence")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "raw_evidence")
        # Must NOT return the technical details menu
        text = result.text.lower()
        self.assertNotIn("what would you like to see", text,
            "show raw evidence must not return technical details menu")

    def test_raw_evidence_contains_paths_or_no_artifacts_message(self):
        result = self._call("show raw evidence")
        self.assertIsNotNone(result)
        text = result.text
        self.assertTrue(
            "docs/reports" in text or "artifact" in text.lower() or "no artifacts" in text.lower(),
            f"Raw evidence response must show paths or explain no artifacts: {text}"
        )

    def test_copied_menu_item_executes_not_loops(self):
        """Copied menu item must execute, not re-show the menu."""
        result = self._call("‘show raw evidence’ — artifact files and paths")
        self.assertIsNotNone(result)
        self.assertNotEqual(result.matched_topic, "technical_details",
            "Copied menu item must not route back to technical_details menu")

    def test_technical_details_still_shows_menu(self):
        """'show technical details' must still show the submenu (unchanged)."""
        result = self._call("show technical details")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "technical_details")
        text = result.text.lower()
        self.assertIn("raw evidence", text, "technical details menu must still list raw evidence option")


class TestTelegramBotNormalization(unittest.TestCase):
    def test_normalize_telegram_command_function_exists(self):
        import telegram_bot as tb
        self.assertTrue(hasattr(tb, "_normalize_telegram_command"))

    def test_normalize_in_bot_strips_smart_quotes(self):
        from telegram_bot import _normalize_telegram_command
        result = _normalize_telegram_command("‘show raw evidence’ — artifact files and paths")
        self.assertEqual(result.lower(), "show raw evidence")

    def test_normalize_in_bot_strips_bullet(self):
        from telegram_bot import _normalize_telegram_command
        result = _normalize_telegram_command("• show raw evidence — artifact files and paths")
        self.assertEqual(result.lower(), "show raw evidence")

    def test_normalize_preserves_normal_command(self):
        from telegram_bot import _normalize_telegram_command
        result = _normalize_telegram_command("show daily research review")
        self.assertEqual(result, "show daily research review")


if __name__ == "__main__":
    unittest.main()
