"""
test_information_sources_common_language.py
=============================================
Verify 'where do you get your information' returns common language,
NOT a raw directory listing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


class TestInformationSourcesCommonLanguage(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_routes_to_information_sources(self):
        result = self._call("where do you get your information")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "information_sources")

    def test_what_did_you_get_your_information_from_routes(self):
        result = self._call("what did you get your information from")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "information_sources")

    def test_response_in_plain_language(self):
        result = self._call("where do you get your information")
        self.assertIsNotNone(result)
        text = result.text
        # Should mention data sources in plain language
        self.assertIn("YouTube", text)

    def test_no_raw_directory_dump(self):
        result = self._call("what are your sources")
        self.assertIsNotNone(result)
        text = result.text
        # Should NOT show raw directory listings
        self.assertNotIn("items)", text,
            "Response must not dump raw directory item counts")
        self.assertNotIn("not yet created", text,
            "Response must not show filesystem status details")

    def test_no_raw_path_dump(self):
        result = self._call("where does this data come from")
        self.assertIsNotNone(result)
        text = result.text
        # Should not dump multiple raw artifact paths
        self.assertFalse(
            text.count("docs/reports/") > 2,
            "Response must not dump multiple raw artifact paths"
        )

    def test_technical_details_phrase_present(self):
        """Response should mention how to get technical details."""
        result = self._call("what files do you read")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("technical", text,
            "Response should tell Ray how to get technical details")

    def test_explains_evidence_only_approach(self):
        result = self._call("how do you know that")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertTrue(
            "evidence" in text or "verified" in text or "sources" in text,
            "Should explain evidence-only approach"
        )

    def test_mentions_github(self):
        result = self._call("what data sources do you use")
        self.assertIsNotNone(result)
        self.assertIn("GitHub", result.text)


class TestInformationSourcesKeywords(unittest.TestCase):
    """Verify all trigger phrases route correctly."""

    def _routes(self, text: str) -> bool:
        from lib.hermes_internal_first import try_internal_first
        result = try_internal_first(text)
        return result is not None and result.matched_topic == "information_sources"

    def test_all_trigger_phrases(self):
        phrases = [
            "where do you get your information",
            "what are your sources",
            "information sources",
            "where does this data come from",
            "what data sources do you use",
            "where does your information come from",
            "how do you know that",
            "where did you get that",
            "what is your source",
            "how do you get your data",
            "what files do you read",
            "what do you read",
            "where do you read from",
            "hermes data sources",
            "what did you get your information from",
            "where did you get your information",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(self._routes(phrase), f"'{phrase}' did not route to information_sources")


if __name__ == "__main__":
    unittest.main()
